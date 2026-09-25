"""
scan_reasoner_branches.py
─────────────────────────
Scans the LEVIR-CD test set (using PyTorch best_model.pt) and collects
examples where the deforestation OR bare-soil classification branches fire.
Stops once we have ≥3 deforestation and ≥3 bare-soil examples, then picks
the top 5 most interesting across both categories (by confidence and
signal strength) and prints their full raw stats.

Run:
    cd satellite_change_detection
    source venv/bin/activate
    python scan_reasoner_branches.py
"""

import os, sys
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import MobileNetV2_3D_CDNet
from change_reasoner import reason_regions

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CKPT_PATH   = os.path.join(SCRIPT_DIR, "best_model.pt")
TEST_DIR    = os.path.join(SCRIPT_DIR, "dataset", "test")
SKIP_FILES  = {"test_102_512_0.png", "test_16_0_256.png", "test_26_512_512.png"}

# ── Device ────────────────────────────────────────────────────────────────────
device = torch.device("mps") if (
    hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
) else torch.device("cpu")
print(f"[device] {device}")

# ── Model ─────────────────────────────────────────────────────────────────────
model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
model.load_state_dict(torch.load(CKPT_PATH, map_location=device))
model.eval()
print(f"[model]  Loaded — {sum(p.numel() for p in model.parameters()):,} params\n")

MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

def prep(path: str):
    img = Image.open(path).convert("RGB").resize((256, 256))
    raw = np.array(img, dtype=np.uint8)
    t   = torch.from_numpy(raw.astype(np.float32) / 255.0).permute(2, 0, 1)
    t   = (t - MEAN) / STD
    return t.unsqueeze(0).to(device), raw

def run_one(fname: str):
    ap = os.path.join(TEST_DIR, "A", fname)
    bp = os.path.join(TEST_DIR, "B", fname)
    lp = os.path.join(TEST_DIR, "label", fname)
    if not (os.path.exists(ap) and os.path.exists(bp) and os.path.exists(lp)):
        return None

    inp_a, rgb_a = prep(ap)
    inp_b, rgb_b = prep(bp)

    with torch.no_grad():
        logits = model(inp_a, inp_b)
    binary = (torch.sigmoid(logits) > 0.5).squeeze().cpu().numpy().astype(np.uint8)

    if binary.sum() < 50:
        return None   # skip no-change images

    regions = reason_regions(rgb_a, rgb_b, binary)
    if not regions:
        return None

    # GT
    gt  = (np.array(Image.open(lp).convert("L").resize((256, 256))) > 127).astype(np.uint8)
    fp  = binary.flatten().astype(float)
    fg  = gt.flatten().astype(float)
    tp  = (fp * fg).sum();  fp_ = (fp * (1-fg)).sum();  fn_ = ((1-fp)*fg).sum()
    iou = tp / (tp + fp_ + fn_) if (tp + fp_ + fn_) > 0 else 0.0

    return {
        "filename": fname,
        "pct": round(float(binary.sum()) / (256*256) * 100, 3),
        "iou": round(iou, 4),
        "regions": regions,
    }

# ── Scan all files ─────────────────────────────────────────────────────────────
all_files = sorted(
    f for f in os.listdir(os.path.join(TEST_DIR, "A"))
    if f.endswith(".png") and f not in SKIP_FILES
)

found_deforestation = []
found_soil          = []
found_unclear       = []

print(f"Scanning {len(all_files)} test files ...\n")
for i, fname in enumerate(all_files):
    result = run_one(fname)
    if result is None:
        continue

    for reg in result["regions"]:
        ct = reg["change_type"]
        entry = {**result, "region": reg}
        if "deforestation" in ct:
            found_deforestation.append(entry)
        elif "soil" in ct:
            found_soil.append(entry)
        elif "unclear" in ct:
            found_unclear.append(entry)

    # Print scan progress every 200 files
    if (i + 1) % 200 == 0:
        print(f"  scanned {i+1}/{len(all_files)} | "
              f"deforestation={len(found_deforestation)} "
              f"soil={len(found_soil)} "
              f"unclear={len(found_unclear)}")

    # Stop early if we have plenty of both
    if len(found_deforestation) >= 5 and len(found_soil) >= 5:
        print(f"  Found enough of both branches at file {i+1}. Stopping early.")
        break

print(f"\nScan complete.")
print(f"  Deforestation examples : {len(found_deforestation)}")
print(f"  Bare-soil examples     : {len(found_soil)}")
print(f"  Unclear examples       : {len(found_unclear)}\n")

# ── Pick 5 most informative (prefer high signal strength) ─────────────────────
# Sort deforestation by veg_ratio_drop desc
found_deforestation.sort(key=lambda e: e["region"]["stats"]["veg_ratio_drop"], reverse=True)
# Sort soil by red_excess_after desc
found_soil.sort(key=lambda e: e["region"]["stats"]["red_excess_after"], reverse=True)

# Build final selection of 5 varied images
selection = []
defore_pool = found_deforestation[:3]
soil_pool   = found_soil[:3]

# interleave
for x in defore_pool: selection.append(("deforestation", x))
for x in soil_pool:   selection.append(("soil", x))
# De-duplicate by filename
seen = set()
unique_sel = []
for cat, e in selection:
    if e["filename"] not in seen:
        seen.add(e["filename"])
        unique_sel.append((cat, e))
# Pad with unclear if we have <5 unique filenames
for e in found_unclear:
    if len(unique_sel) >= 5: break
    if e["filename"] not in seen:
        seen.add(e["filename"])
        unique_sel.append(("unclear", e))

unique_sel = unique_sel[:5]

# ── Print full raw output ─────────────────────────────────────────────────────
SEP = "=" * 72
print(SEP)
print(f"SELECTED 5 IMAGES (raw stats, no summarisation)")
print(SEP + "\n")

for rank, (cat, entry) in enumerate(unique_sel, 1):
    reg = entry["region"]
    bb  = reg["bounding_box"]
    st  = reg["stats"]
    print(SEP)
    print(f"Example {rank}  [{cat.upper()} branch fired]  |  {entry['filename']}")
    print(SEP)
    print(f"  GT IoU             : {entry['iou']}")
    print(f"  % image changed    : {entry['pct']:.3f}%")
    print()
    print(f"  Region bounding_box     : x={bb[0]} y={bb[1]} w={bb[2]} h={bb[3]}")
    print(f"  Region pixel_area       : {reg['pixel_area']:,}")
    print(f"  change_type             : {reg['change_type']}")
    print(f"  confidence_label        : {reg['confidence_label']}")
    print(f"  stats →")
    for k, v in st.items():
        print(f"    {k:<26} = {v}")
    print()
