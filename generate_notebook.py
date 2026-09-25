#!/usr/bin/env python3
"""Generate colab_training.ipynb with FULL contents from dataset.py and model.py."""
import json
import os

PROJ = "/Volumes/My Passport/Projects/Mini Project/satellite_change_detection"
OUT  = "/Users/aravind/.gemini/antigravity-ide/brain/e754aa6a-0ce4-4a09-a779-5a62c9be5b1c/colab_training.ipynb"

# ── Read the real source files ────────────────────────────────────────
with open(os.path.join(PROJ, "dataset.py"), "r") as f:
    raw_dataset = f.read()

with open(os.path.join(PROJ, "model.py"), "r") as f:
    raw_model = f.read()

# Strip top-level imports (they're in the imports cell already)
def strip_imports(src):
    lines = src.split("\n")
    kept = []
    for line in lines:
        if line.startswith("import ") or line.startswith("from "):
            continue
        kept.append(line)
    # Remove leading blank lines
    while kept and kept[0].strip() == "":
        kept.pop(0)
    return "\n".join(kept)

dataset_cell_source = strip_imports(raw_dataset)
model_cell_source   = strip_imports(raw_model)

# ── Build the notebook by hand as a dict ──────────────────────────────
def make_md(source_str):
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source_str.split("\n")  # will be joined by nbformat readers
    }

def make_code(source_str):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source_str
    }

training_code = r'''def calculate_iou(preds, labels):
    preds = (torch.sigmoid(preds) > 0.5).float()
    intersection = (preds * labels).sum()
    union = preds.sum() + labels.sum() - intersection
    if union == 0:
        return 1.0
    return (intersection / union).item()

def dice_bce_loss(inputs, targets, smooth=1):
    bce = F.binary_cross_entropy_with_logits(inputs, targets, reduction='mean')
    inputs = torch.sigmoid(inputs)
    inputs_flat = inputs.view(-1)
    targets_flat = targets.view(-1)
    intersection = (inputs_flat * targets_flat).sum()
    dice = 1 - (2.*intersection + smooth)/(inputs_flat.sum() + targets_flat.sum() + smooth)
    return bce + dice

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)

# ── Device ────────────────────────────────────────────────────────────
if torch.cuda.is_available():
    device = torch.device('cuda')
else:
    try:
        if torch.backends.mps.is_available():
            device = torch.device('mps')
        else:
            device = torch.device('cpu')
    except AttributeError:
        device = torch.device('cpu')
print(f"Using device: {device}")

# ── Hyperparameters ───────────────────────────────────────────────────
epochs = 100
batch_size = 4
lr = 5e-4
patience_limit = 10
dataset_dir = 'dataset'

# ── DataLoaders ───────────────────────────────────────────────────────
train_dataset = ChangeDetectionDataset(dataset_dir, split='train')
val_dataset   = ChangeDetectionDataset(dataset_dir, split='val')
test_dataset  = ChangeDetectionDataset(dataset_dir, split='test')

train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
val_loader   = DataLoader(val_dataset,   batch_size=batch_size, shuffle=False)
test_loader  = DataLoader(test_dataset,  batch_size=batch_size, shuffle=False)

print(f"Train: {len(train_dataset)} patches, Val: {len(val_dataset)} patches, Test: {len(test_dataset)} patches")

# ── Model, Optimizer, Scheduler ──────────────────────────────────────
model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
print(f"Model parameters: {count_parameters(model) / 1e6:.2f}M")

optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

# ── Training Loop ────────────────────────────────────────────────────
best_iou = 0.0
patience = 0
start_time = time.time()
log_f = open("training_log.txt", "w")

for epoch in range(epochs):
    model.train()
    train_loss = 0
    train_iou = 0

    pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs} [Train]")
    for img_a, img_b, label in pbar:
        img_a  = img_a.to(device)
        img_b  = img_b.to(device)
        label  = label.to(device)

        optimizer.zero_grad()
        outputs = model(img_a, img_b)

        loss = dice_bce_loss(outputs, label)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        train_iou  += calculate_iou(outputs, label)

        pbar.set_postfix({'loss': f"{loss.item():.4f}"})

    scheduler.step()

    avg_train_loss = train_loss / len(train_loader)
    avg_train_iou  = train_iou  / len(train_loader)

    # ── Validation ────────────────────────────────────────────────────
    model.eval()
    val_loss = 0
    val_iou  = 0

    with torch.no_grad():
        for img_a, img_b, label in tqdm(val_loader, desc=f"Epoch {epoch+1}/{epochs} [Val]"):
            img_a  = img_a.to(device)
            img_b  = img_b.to(device)
            label  = label.to(device)

            outputs = model(img_a, img_b)
            loss = dice_bce_loss(outputs, label)

            val_loss += loss.item()
            val_iou  += calculate_iou(outputs, label)

    avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0
    avg_val_iou  = val_iou  / len(val_loader) if len(val_loader) > 0 else 0

    log_str = (f"Epoch {epoch+1}: Train Loss: {avg_train_loss:.4f}, "
               f"Train IoU: {avg_train_iou:.4f} | "
               f"Val Loss: {avg_val_loss:.4f}, Val IoU: {avg_val_iou:.4f} | "
               f"LR: {scheduler.get_last_lr()[0]:.6f}")
    print(log_str)
    log_f.write(log_str + "\n")

    if avg_val_iou >= best_iou:
        best_iou = avg_val_iou
        torch.save(model.state_dict(), 'best_model.pt')
        print("  -> Saved new best model.")
        log_f.write("Saved new best model.\n")
        patience = 0
    else:
        patience += 1
        msg = f"  -> Val IoU did not improve. Patience: {patience}/{patience_limit}"
        print(msg)
        log_f.write(msg.strip() + "\n")

    if patience >= patience_limit:
        msg = f"Early stopping triggered after {epoch+1} epochs."
        print(msg)
        log_f.write(msg + "\n")
        break

end_time = time.time()
total_time = end_time - start_time
print(f"\nTraining completed in {total_time:.2f}s ({total_time/3600:.2f}h).")
log_f.write(f"Training completed in {total_time:.2f}s ({total_time/3600:.2f}h).\n")
print(f"Best Validation IoU: {best_iou:.4f}")
log_f.write(f"Best Validation IoU: {best_iou:.4f}\n")

# ── Test Evaluation ──────────────────────────────────────────────────
print("\n--- Evaluating on Test Set ---")
log_f.write("\n--- Evaluating on Test Set ---\n")
model.load_state_dict(torch.load('best_model.pt'))
model.eval()
test_loss = 0
test_iou  = 0
with torch.no_grad():
    for img_a, img_b, label in tqdm(test_loader, desc="Test Evaluation"):
        img_a  = img_a.to(device)
        img_b  = img_b.to(device)
        label  = label.to(device)

        outputs = model(img_a, img_b)
        loss = dice_bce_loss(outputs, label)

        test_loss += loss.item()
        test_iou  += calculate_iou(outputs, label)

avg_test_loss = test_loss / len(test_loader) if len(test_loader) > 0 else 0
avg_test_iou  = test_iou  / len(test_loader) if len(test_loader) > 0 else 0
msg = f"Test Loss: {avg_test_loss:.4f}, Test IoU: {avg_test_iou:.4f}"
print(msg)
log_f.write(msg + "\n")
log_f.close()
print("Training log saved to training_log.txt")
'''

notebook = {
    "nbformat": 4,
    "nbformat_minor": 4,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.12"
        }
    },
    "cells": [
        make_md("# 1. Install Dependencies"),
        make_code("!pip install torch torchvision tqdm Pillow"),

        make_md("# 2. Upload and Extract Dataset\n**Upload `dataset.zip` (pre-cropped 256×256 patches with `train/`, `val/`, `test/` folders) then run this cell.**"),
        make_code("!unzip -q dataset.zip -d ."),

        make_md("# 3. Imports"),
        make_code("import os\nimport time\nimport torch\nimport torch.nn as nn\nimport torch.nn.functional as F\nimport torch.optim as optim\nimport torchvision.models as models\nimport torchvision.transforms as transforms\nfrom PIL import Image\nfrom torch.utils.data import Dataset, DataLoader\nfrom torch.optim.lr_scheduler import CosineAnnealingLR\nfrom tqdm import tqdm"),

        make_md("# 4. Dataset Loader"),
        make_code(dataset_cell_source),

        make_md("# 5. Model Architecture"),
        make_code(model_cell_source),

        make_md("# 6. Training & Evaluation"),
        make_code(training_code),

        make_md("# 7. Download Results"),
        make_code("!zip training_results.zip best_model.pt training_log.txt\nfrom google.colab import files\nfiles.download('training_results.zip')"),
    ]
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

# ── Verification: print cell 4 and cell 5 contents ───────────────────
print("=" * 70)
print("CELL 4 (Dataset Loader) — first 10 lines:")
print("=" * 70)
c4 = notebook["cells"][7]["source"]  # index 7 = code cell after md "4. Dataset Loader"
for line in c4.split("\n")[:10]:
    print(line)
print(f"... ({len(c4.split(chr(10)))} total lines)")

print()
print("=" * 70)
print("CELL 5 (Model Architecture) — first 15 lines:")
print("=" * 70)
c5 = notebook["cells"][9]["source"]  # index 9 = code cell after md "5. Model Architecture"
for line in c5.split("\n")[:15]:
    print(line)
print(f"... ({len(c5.split(chr(10)))} total lines)")

print()
print("=" * 70)
print(f"Notebook written to {OUT}")
print(f"Total cells: {len(notebook['cells'])}")
print("=" * 70)
