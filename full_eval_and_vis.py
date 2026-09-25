"""
full_eval_and_vis.py
Real inference evaluation + qualitative visualization on the LEVIR-CD test set.
Saves 6 qualitative panels and prints exact metrics (no simulations).
"""

import os
import sys
import json
import random

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tqdm import tqdm

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT   = os.path.join(SCRIPT_DIR, "best_model.pt")
DATASET_DIR  = os.path.join(SCRIPT_DIR, "dataset")
OUTPUT_DIR   = "/Users/aravind/.gemini/antigravity-ide/brain/350dbc5a-f074-4ceb-a9bd-2af909f12ef1"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── local imports ──────────────────────────────────────────────────────────────
sys.path.insert(0, SCRIPT_DIR)
from dataset import ChangeDetectionDataset
from model   import MobileNetV2_3D_CDNet

# ──────────────────────────────────────────────────────────────────────────────
# 1. Device
# ──────────────────────────────────────────────────────────────────────────────
if torch.cuda.is_available():
    device = torch.device("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = torch.device("mps")
else:
    device = torch.device("cpu")
print(f"[device] {device}")

# ──────────────────────────────────────────────────────────────────────────────
# 2. Load model & verify checkpoint
# ──────────────────────────────────────────────────────────────────────────────
print(f"\n[checkpoint] Loading {CHECKPOINT}")
model = MobileNetV2_3D_CDNet(n_classes=1).to(device)

state = torch.load(CHECKPOINT, map_location=device)
model.load_state_dict(state)
print("[checkpoint] load_state_dict() succeeded — no key errors.")

total_params     = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"[params] Total     : {total_params:,}  ({total_params/1e6:.4f} M)")
print(f"[params] Trainable : {trainable_params:,}  ({trainable_params/1e6:.4f} M)")

model.eval()

# ──────────────────────────────────────────────────────────────────────────────
# 3. Dataset
# ──────────────────────────────────────────────────────────────────────────────
test_dataset = ChangeDetectionDataset(DATASET_DIR, split="test")
print(f"\n[dataset] Test samples : {len(test_dataset)}")
test_loader  = DataLoader(test_dataset, batch_size=1, shuffle=False, num_workers=0)

# ──────────────────────────────────────────────────────────────────────────────
# 4. Full evaluation
# ──────────────────────────────────────────────────────────────────────────────
total_tp = total_fp = total_fn = total_tn = 0

# We'll also collect per-sample stats for qualitative selection
sample_records = []   # list of dicts

print("\n[eval] Running full test-set evaluation …")
with torch.no_grad():
    for idx, (img_a, img_b, label) in enumerate(tqdm(test_loader, desc="Evaluating")):
        img_a  = img_a.to(device)
        img_b  = img_b.to(device)
        label  = label.to(device)

        logits = model(img_a, img_b)
        prob   = torch.sigmoid(logits)
        pred   = (prob > 0.5).float()

        flat_pred  = pred.view(-1)
        flat_label = label.view(-1)

        tp = (flat_pred * flat_label).sum().item()
        fp = (flat_pred * (1 - flat_label)).sum().item()
        fn = ((1 - flat_pred) * flat_label).sum().item()
        tn = ((1 - flat_pred) * (1 - flat_label)).sum().item()

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

        # per-sample IoU for qualitative selection
        s_iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 1.0
        s_f1_num = 2 * tp
        s_f1_den = 2 * tp + fp + fn
        s_f1  = s_f1_num / s_f1_den if s_f1_den > 0 else 1.0
        gt_px = flat_label.sum().item()

        sample_records.append({
            "idx": idx,
            "filename": test_dataset.filenames[idx],
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "iou": s_iou,
            "f1": s_f1,
            "gt_px": gt_px,
            # store tensors on CPU for later vis
            "img_a":  img_a.squeeze(0).cpu(),
            "img_b":  img_b.squeeze(0).cpu(),
            "label":  label.squeeze(0).cpu(),
            "prob":   prob.squeeze(0).cpu(),
            "pred":   pred.squeeze(0).cpu(),
        })

# ── aggregate metrics ─────────────────────────────────────────────────────────
precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
recall    = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
f1        = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
iou       = total_tp / (total_tp + total_fp + total_fn) if (total_tp + total_fp + total_fn) > 0 else 0.0

print("\n" + "="*50)
print("EVALUATION RESULTS (real inference on LEVIR-CD test set)")
print("="*50)
print(f"  Total TP : {total_tp:,.0f}")
print(f"  Total FP : {total_fp:,.0f}")
print(f"  Total FN : {total_fn:,.0f}")
print(f"  Total TN : {total_tn:,.0f}")
print(f"  Precision: {precision:.4f}  ({precision*100:.2f}%)")
print(f"  Recall   : {recall:.4f}  ({recall*100:.2f}%)")
print(f"  F1 Score : {f1:.4f}  ({f1*100:.2f}%)")
print(f"  IoU      : {iou:.4f}  ({iou*100:.2f}%)")
print("="*50)

metrics = {
    "precision": precision,
    "recall":    recall,
    "f1":        f1,
    "iou":       iou,
    "total_tp":  total_tp,
    "total_fp":  total_fp,
    "total_fn":  total_fn,
    "total_tn":  total_tn,
    "num_test_samples": len(test_dataset),
}
with open(os.path.join(OUTPUT_DIR, "eval_metrics.json"), "w") as fj:
    json.dump(metrics, fj, indent=2)
print(f"[metrics] Saved to {OUTPUT_DIR}/eval_metrics.json")

# ──────────────────────────────────────────────────────────────────────────────
# 5. Select 6 qualitative examples
#    - 4 good cases (high IoU, has real changed pixels)
#    - 1 false-positive failure  (fp >> fn, high fp ratio)
#    - 1 false-negative failure  (fn >> fp, model missed real change)
# ──────────────────────────────────────────────────────────────────────────────
# Filter only samples that have actual changed pixels in GT
has_change = [r for r in sample_records if r["gt_px"] > 100]

# Sort by IoU descending
has_change_sorted = sorted(has_change, key=lambda x: x["iou"], reverse=True)

# Good cases: top IoU with real change
good_cases = has_change_sorted[:4]

# FP failure: fp / (fp + tp) highest, must have gt_px > 100
fp_heavy = sorted(has_change, key=lambda x: x["fp"] / max(x["fp"] + x["tp"], 1), reverse=True)
fp_failure = fp_heavy[0]

# FN failure: fn / (fn + tp) highest, must have gt_px > 100
fn_heavy = sorted(has_change, key=lambda x: x["fn"] / max(x["fn"] + x["tp"], 1), reverse=True)
fn_failure = fn_heavy[0]

qualitative_samples = good_cases + [fp_failure, fn_failure]

# ──────────────────────────────────────────────────────────────────────────────
# 6. Denormalize helper
# ──────────────────────────────────────────────────────────────────────────────
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

def denorm(t):
    """Denormalize image tensor [3,H,W] → numpy [H,W,3] uint8."""
    img = t * STD + MEAN
    img = img.permute(1, 2, 0).numpy()
    img = np.clip(img, 0, 1)
    return (img * 255).astype(np.uint8)

# ──────────────────────────────────────────────────────────────────────────────
# 7. Generate qualitative panels
# ──────────────────────────────────────────────────────────────────────────────
LABELS = ["good_1", "good_2", "good_3", "good_4", "fp_failure", "fn_failure"]
qual_info = []

for panel_idx, (rec, label_str) in enumerate(zip(qualitative_samples, LABELS)):
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    fig.patch.set_facecolor("#111111")

    img_a_np = denorm(rec["img_a"])
    img_b_np = denorm(rec["img_b"])
    gt_np    = rec["label"].squeeze(0).numpy()
    prob_np  = rec["prob"].squeeze(0).numpy()
    pred_np  = rec["pred"].squeeze(0).numpy()

    # Build colour-coded overlay: TP=green, FP=red, FN=yellow
    H, W = gt_np.shape
    overlay = np.zeros((H, W, 3), dtype=np.uint8)
    gt_bool   = gt_np   > 0.5
    pred_bool = pred_np > 0.5
    overlay[gt_bool & pred_bool]   = [0,   200, 0]    # TP  green
    overlay[pred_bool & ~gt_bool]  = [220, 0,   0]    # FP  red
    overlay[gt_bool & ~pred_bool]  = [255, 220, 0]    # FN  yellow

    titles = ["Before (A)", "After (B)", "GT  vs  Pred\n(green=TP, red=FP, yellow=FN)", "Probability Map"]
    images = [img_a_np, img_b_np, overlay, prob_np]
    cmaps  = [None, None, None, "hot"]

    for ax, im, title, cmap in zip(axes, images, titles, cmaps):
        ax.set_facecolor("#111111")
        if cmap:
            ax.imshow(im, cmap=cmap, vmin=0, vmax=1)
        else:
            ax.imshow(im)
        ax.set_title(title, color="white", fontsize=11, pad=6)
        ax.axis("off")

    # Compute per-sample stats for title
    tp_s = rec["tp"]; fp_s = rec["fp"]; fn_s = rec["fn"]
    iou_s = rec["iou"]; f1_s = rec["f1"]

    suptitle_text = (
        f"[{label_str.upper()}]  File: {rec['filename']}  |  "
        f"IoU={iou_s:.3f}  F1={f1_s:.3f}  TP={int(tp_s):,}  FP={int(fp_s):,}  FN={int(fn_s):,}"
    )
    fig.suptitle(suptitle_text, color="white", fontsize=9, y=1.01)
    plt.tight_layout()

    out_path = os.path.join(OUTPUT_DIR, f"qual_{panel_idx+1:02d}_{label_str}.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"[qual] Saved panel {panel_idx+1}: {out_path}")

    qual_info.append({
        "panel": panel_idx + 1,
        "type": label_str,
        "filename": rec["filename"],
        "iou": iou_s,
        "f1": f1_s,
        "tp": int(tp_s), "fp": int(fp_s), "fn": int(fn_s),
        "path": out_path,
    })

with open(os.path.join(OUTPUT_DIR, "qualitative_info.json"), "w") as fj:
    json.dump(qual_info, fj, indent=2)

print("\n[DONE] All outputs saved.")
print(f"  Metrics  → {OUTPUT_DIR}/eval_metrics.json")
print(f"  Panels   → {OUTPUT_DIR}/qual_XX_*.png")
