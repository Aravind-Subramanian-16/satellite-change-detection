"""
Show a representative 4x3 grid: 4 images, each showing:
  Col 1: Image B at 0.5m
  Col 2: Pred Mask at 0.5m  
  Col 3: Image B at 10m
  Col 4: Pred Mask at 10m
  Col 5: Ground Truth

Pick images that represent the actual distribution:
  - 2 images where 10m mask is blank (the 98.8% majority)
  - 1 image where 10m mask is blobby (the ~1% outlier)
  - 1 image where model still gets something right at 10m (the 0.2% fluke)
"""
import os
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageFilter
from model import MobileNetV2_3D_CDNet

def preprocess_numpy(img_rgb):
    img_array = img_rgb.astype(np.float32) / 255.0
    img_array = np.transpose(img_array, (2, 0, 1))
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
    img_array = (img_array - mean) / std
    return img_array

def degrade_image(img_arr, factor):
    if factor == 1:
        return img_arr
    img = Image.fromarray(img_arr)
    sigma = factor / 2.0
    blurred = img.filter(ImageFilter.GaussianBlur(radius=sigma))
    w, h = img.size
    new_w, new_h = w // factor, h // factor
    downsampled = blurred.resize((new_w, new_h), resample=Image.LANCZOS)
    upsampled = downsampled.resize((w, h), resample=Image.LANCZOS)
    return np.array(upsampled)

df = pd.read_csv('degradation_results.csv')

# Filter to images with real change at 1x
df_1x = df[(df['factor'] == 1) & (df['iou'] > 0.5)]
df_20x = df[df['factor'] == 20]

merged = df_1x[['image', 'iou', 'tp', 'fp', 'fn']].merge(
    df_20x[['image', 'iou', 'tp', 'fp', 'fn', 'f1']],
    on='image', suffixes=('_1x', '_20x')
)

# Category 1: 10m mask is completely blank (tp_20x == 0 and fp_20x == 0)
blank_at_10m = merged[(merged['tp_20x'] == 0) & (merged['fp_20x'] == 0)].sort_values('iou_1x', ascending=False)

# Category 2: 10m mask is blobby/wrong (has predictions but low IoU)
blobby_at_10m = merged[(merged['tp_20x'] + merged['fp_20x'] > 100) & (merged['iou_20x'] < 0.3)].sort_values('tp_20x', ascending=False)

# Category 3: 10m mask still decent (IoU > 0.3)
ok_at_10m = merged[merged['iou_20x'] >= 0.3].sort_values('iou_20x', ascending=False)

print(f"Blank at 10m (from good 1x images): {len(blank_at_10m)}")
print(f"Blobby at 10m: {len(blobby_at_10m)}")
print(f"OK at 10m: {len(ok_at_10m)}")

picks = []
labels = []

# 2 blank examples
for _, row in blank_at_10m.head(2).iterrows():
    picks.append(row['image'])
    labels.append(f"BLANK at 10m (1x IoU={row['iou_1x']:.2f})")

# 1 blobby
if len(blobby_at_10m) > 0:
    row = blobby_at_10m.iloc[0]
    picks.append(row['image'])
    labels.append(f"BLOBBY at 10m (IoU={row['iou_20x']:.2f})")
    
# 1 ok (if any)
if len(ok_at_10m) > 0:
    row = ok_at_10m.iloc[0]
    picks.append(row['image'])
    labels.append(f"OUTLIER at 10m (IoU={row['iou_20x']:.2f})")

print(f"\nSelected {len(picks)} images: {picks}")
print(f"Labels: {labels}")

# Load model
device = torch.device('cpu')
model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
state = torch.load("best_model.pt", map_location=device)
model.load_state_dict(state)
model.eval()

fig, axes = plt.subplots(len(picks), 5, figsize=(16, 3.5 * len(picks)))
col_titles = ["Image B (0.5m)", "Pred Mask (0.5m)", "Image B (10m)", "Pred Mask (10m)", "Ground Truth"]

for c in range(5):
    axes[0, c].set_title(col_titles[c], fontsize=11, fontweight='bold')

for row_idx, (filename, label) in enumerate(zip(picks, labels)):
    path_a = os.path.join("dataset/test/A", filename)
    path_b = os.path.join("dataset/test/B", filename)
    path_label = os.path.join("dataset/test/label", filename)
    
    img_a = np.array(Image.open(path_a).convert("RGB"))
    img_b = np.array(Image.open(path_b).convert("RGB"))
    gt = np.array(Image.open(path_label).convert("L"))
    gt_mask = (gt > 0).astype(np.uint8)
    
    deg20_a = degrade_image(img_a, 20)
    deg20_b = degrade_image(img_b, 20)
    
    in1_a = preprocess_numpy(img_a)
    in1_b = preprocess_numpy(img_b)
    in20_a = preprocess_numpy(deg20_a)
    in20_b = preprocess_numpy(deg20_b)
    
    t_a = torch.tensor(np.stack([in1_a, in20_a])).to(device)
    t_b = torch.tensor(np.stack([in1_b, in20_b])).to(device)
    
    with torch.no_grad():
        logits = model(t_a, t_b)
        probs = torch.sigmoid(logits).cpu().numpy()
        preds = (probs > 0.5).astype(np.uint8)[:, 0]
    
    pred1 = preds[0]
    pred20 = preds[1]
    
    pred_px_1x = pred1.sum()
    pred_px_20x = pred20.sum()
    
    axes[row_idx, 0].imshow(img_b)
    axes[row_idx, 1].imshow(pred1 * 255, cmap='gray', vmin=0, vmax=255)
    axes[row_idx, 2].imshow(deg20_b)
    axes[row_idx, 3].imshow(pred20 * 255, cmap='gray', vmin=0, vmax=255)
    axes[row_idx, 4].imshow(gt_mask * 255, cmap='gray', vmin=0, vmax=255)
    
    axes[row_idx, 0].set_ylabel(label, fontsize=9, rotation=0, labelpad=120, va='center')
    
    # Annotate pixel counts
    axes[row_idx, 1].text(5, 245, f"{pred_px_1x:,} px", color='lime', fontsize=8, 
                           bbox=dict(facecolor='black', alpha=0.7))
    axes[row_idx, 3].text(5, 245, f"{pred_px_20x:,} px", color='lime', fontsize=8,
                           bbox=dict(facecolor='black', alpha=0.7))
    
    for c in range(5):
        axes[row_idx, c].axis('off')

plt.suptitle("Representative Degradation Examples (98.8% of images produce BLANK masks at 10m)", 
             fontsize=13, fontweight='bold', y=1.01)
plt.tight_layout()
plt.savefig('visual_degradation_proof_v2.png', dpi=150, bbox_inches='tight')
print("Saved visual_degradation_proof_v2.png")
