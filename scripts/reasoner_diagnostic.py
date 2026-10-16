"""
test_reasoner.py
────────────────
Run the full pipeline (PyTorch inference → binary mask → change_reasoner)
on 3 real LEVIR-CD test images and print exact output for each.
Uses best_model.pt directly (the ONNX file in this project was exported
from a different checkpoint and is not used here).

Usage:
    cd satellite_change_detection
    source venv/bin/activate
    python test_reasoner.py
"""

import os, sys
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import MobileNetV2_3D_CDNet
from change_reasoner import reason_regions, MIN_REGION_AREA

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CKPT_PATH    = os.path.join(SCRIPT_DIR, "best_model.pt")
DATASET_DIR  = os.path.join(SCRIPT_DIR, "dataset", "test")

# Three representative test images from LEVIR-CD test split
TEST_FILES = [
    "test_102_512_0.png",   # high-IoU good detection (IoU=0.975 in full eval)
    "test_16_0_256.png",    # large building footprint (IoU=0.973)
    "test_26_512_512.png",  # failure tile: spatially disjoint FP+FN
]

# ── Device ────────────────────────────────────────────────────────────────────
if torch.cuda.is_available():
    device = torch.device("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"[device]     {device}")

# ── Load model ────────────────────────────────────────────────────────────────
print(f"[checkpoint] Loading {CKPT_PATH}")
model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
model.load_state_dict(torch.load(CKPT_PATH, map_location=device))
model.eval()
print(f"[checkpoint] Loaded OK — {sum(p.numel() for p in model.parameters()):,} params\n")

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

def preprocess(path: str):
    """Returns (normalised_tensor_1CHW, raw_rgb_uint8_HW3)."""
    img = Image.open(path).convert("RGB").resize((256, 256))
    raw = np.array(img, dtype=np.uint8)                   # [256,256,3]
    t   = torch.from_numpy(raw.astype(np.float32) / 255.0).permute(2, 0, 1)
    t   = (t - MEAN) / STD
    return t.unsqueeze(0).to(device), raw

def run_image(filename: str) -> dict:
    a_path = os.path.join(DATASET_DIR, "A",     filename)
    b_path = os.path.join(DATASET_DIR, "B",     filename)
    l_path = os.path.join(DATASET_DIR, "label", filename)

    inp_a, rgb_a = preprocess(a_path)
    inp_b, rgb_b = preprocess(b_path)

    # ── Inference ────────────────────────────────────────────────────────────
    with torch.no_grad():
        logits = model(inp_a, inp_b)
    prob   = torch.sigmoid(logits)
    binary = (prob > 0.5).squeeze().cpu().numpy().astype(np.uint8)  # [256,256]

    pct_changed = float(np.sum(binary)) / (256 * 256) * 100.0

    prob_np = prob.squeeze().cpu().numpy()

    # ── Reasoning ────────────────────────────────────────────────────────────
    regions = reason_regions(rgb_a, rgb_b, binary)

    # ── GT metrics ───────────────────────────────────────────────────────────
    gt_img = Image.open(l_path).convert("L").resize((256, 256))
    gt     = (np.array(gt_img) > 127).astype(np.uint8)
    flat_p = binary.flatten().astype(float)
    flat_g = gt.flatten().astype(float)
    tp = (flat_p * flat_g).sum()
    fp = (flat_p * (1 - flat_g)).sum()
    fn = ((1 - flat_p) * flat_g).sum()
    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    f1  = 2*tp / (2*tp + fp + fn) if (2*tp + fp + fn) > 0 else 0.0

    return {
        "filename":             filename,
        "gt_metrics":           {"tp": int(tp), "fp": int(fp), "fn": int(fn),
                                 "iou": round(iou, 4), "f1": round(f1, 4)},
        "percent_changed":      round(pct_changed, 4),
        "prob_range":           [round(float(prob_np.min()), 4),
                                 round(float(prob_np.max()), 4)],
        "num_regions_detected": len(regions),
        "change_regions":       regions,
    }

# ── Run all three ──────────────────────────────────────────────────────────────
SEP = "=" * 72

for fname in TEST_FILES:
    print(SEP)
    print(f"IMAGE: {fname}")
    print(SEP)
    result = run_image(fname)

    print(f"  GT metrics          : TP={result['gt_metrics']['tp']:,}  "
          f"FP={result['gt_metrics']['fp']:,}  FN={result['gt_metrics']['fn']:,}  "
          f"IoU={result['gt_metrics']['iou']}  F1={result['gt_metrics']['f1']}")
    print(f"  % image changed     : {result['percent_changed']:.4f}%")
    print(f"  Prob range          : [{result['prob_range'][0]}, {result['prob_range'][1]}]")
    print(f"  Connected regions   : {result['num_regions_detected']} "
          f"(min size = {MIN_REGION_AREA} px)")
    print()

    if not result["change_regions"]:
        print("  [No regions detected above minimum area threshold]")
    else:
        for i, reg in enumerate(result["change_regions"], 1):
            bb = reg["bounding_box"]
            st = reg["stats"]
            print(f"  Region {i:02d}:")
            print(f"    bounding_box     : x={bb[0]} y={bb[1]} w={bb[2]} h={bb[3]}")
            print(f"    pixel_area       : {reg['pixel_area']:,}")
            print(f"    change_type      : {reg['change_type']}")
            print(f"    confidence_label : {reg['confidence_label']}")
            print(f"    stats →")
            for k, v in st.items():
                print(f"      {k:<24} = {v}")
            print()

    print()

print(SEP)
print("Done. Raw output, no summarisation.")
