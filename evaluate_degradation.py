import os
import io
import torch
import numpy as np
import pandas as pd
from PIL import Image, ImageFilter
from tqdm import tqdm
from model import MobileNetV2_3D_CDNet

def preprocess_numpy(img_rgb):
    img_array = img_rgb.astype(np.float32) / 255.0
    img_array = np.transpose(img_array, (2, 0, 1)) # HWC to CHW

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

def run_degradation_experiment():
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"[device] {device}")

    model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
    state = torch.load("best_model.pt", map_location=device)
    model.load_state_dict(state)
    model.eval()

    factors = [1, 2, 4, 8, 16, 20]
    resolutions = {1: "0.5m", 2: "1.0m", 4: "2.0m", 8: "4.0m", 16: "8.0m", 20: "10.0m"}

    test_dir_A = "dataset/test/A"
    test_dir_B = "dataset/test/B"
    test_dir_label = "dataset/test/label"

    files = sorted(os.listdir(test_dir_A))
    results = []

    with torch.no_grad():
        for filename in tqdm(files, desc="Processing images"):
            if not filename.endswith((".png", ".jpg")):
                continue

            path_a = os.path.join(test_dir_A, filename)
            path_b = os.path.join(test_dir_B, filename)
            path_label = os.path.join(test_dir_label, filename)

            img_a = np.array(Image.open(path_a).convert("RGB"))
            img_b = np.array(Image.open(path_b).convert("RGB"))
            label = np.array(Image.open(path_label).convert("L"))
            gt_mask = (label > 0).astype(np.uint8)

            if img_a.shape[:2] != (256, 256):
                img_a = np.array(Image.fromarray(img_a).resize((256, 256), resample=Image.LANCZOS))
                img_b = np.array(Image.fromarray(img_b).resize((256, 256), resample=Image.LANCZOS))
                gt_mask = np.array(Image.fromarray(gt_mask).resize((256, 256), resample=Image.NEAREST))

            batch_a = []
            batch_b = []

            for factor in factors:
                deg_a = degrade_image(img_a, factor)
                deg_b = degrade_image(img_b, factor)
                batch_a.append(preprocess_numpy(deg_a))
                batch_b.append(preprocess_numpy(deg_b))

            # Stack along batch dimension (since each is [3, 256, 256])
            t_a = torch.tensor(np.stack(batch_a)).to(device)
            t_b = torch.tensor(np.stack(batch_b)).to(device)

            logits = model(t_a, t_b) # [6, 1, 256, 256]
            probs = torch.sigmoid(logits).cpu().numpy()
            preds = (probs > 0.5).astype(np.uint8)[:, 0] # [6, 256, 256]

            for i, factor in enumerate(factors):
                pred_mask = preds[i]

                tp = np.sum((pred_mask == 1) & (gt_mask == 1))
                fp = np.sum((pred_mask == 1) & (gt_mask == 0))
                fn = np.sum((pred_mask == 0) & (gt_mask == 1))

                precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0

                results.append({
                    "image": filename,
                    "factor": factor,
                    "real_world_resolution": resolutions[factor],
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "iou": iou,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn
                })

    df = pd.DataFrame(results)
    df.to_csv("degradation_results.csv", index=False)

    grouped = df.groupby('factor')[['tp', 'fp', 'fn']].sum()

    df_positive = df[df['tp'] + df['fn'] > 0]
    macro_stats = df_positive.groupby('factor').agg(
        iou_mean=('iou', 'mean'),
        iou_std=('iou', 'std'),
        f1_mean=('f1', 'mean'),
        f1_std=('f1', 'std'),
        precision_mean=('precision', 'mean'),
        precision_std=('precision', 'std'),
        recall_mean=('recall', 'mean'),
        recall_std=('recall', 'std')
    )

    print("\n=== DEGRADATION SUMMARY ===")
    for factor in factors:
        res = resolutions[factor]
        tps = grouped.loc[factor, 'tp']
        fps = grouped.loc[factor, 'fp']
        fns = grouped.loc[factor, 'fn']

        micro_prec = tps / (tps + fps) if (tps + fps) > 0 else 0.0
        micro_rec = tps / (tps + fns) if (tps + fns) > 0 else 0.0
        micro_f1 = 2 * (micro_prec * micro_rec) / (micro_prec + micro_rec) if (micro_prec + micro_rec) > 0 else 0.0
        micro_iou = tps / (tps + fps + fns) if (tps + fps + fns) > 0 else 0.0

        print(f"\nFactor {factor}x ({res}):")
        print(f"  Micro-Avg -> F1: {micro_f1:.4f} | IoU: {micro_iou:.4f} | Prec: {micro_prec:.4f} | Rec: {micro_rec:.4f}")
        if factor in macro_stats.index:
            row = macro_stats.loc[factor]
            print(f"  Macro-Avg -> F1: {row['f1_mean']:.4f} ± {row['f1_std']:.4f} | IoU: {row['iou_mean']:.4f} ± {row['iou_std']:.4f}")

if __name__ == "__main__":
    run_degradation_experiment()
