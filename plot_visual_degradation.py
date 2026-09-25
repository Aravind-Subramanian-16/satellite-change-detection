import os
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageFilter
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

def run():
    # Find two good images
    df = pd.read_csv('degradation_results.csv')
    df_1x = df[df['factor'] == 1].sort_values('tp', ascending=False)
    # Pick top 2
    filenames = df_1x['image'].values[:2]
    
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
    state = torch.load("best_model.pt", map_location=device)
    model.load_state_dict(state)
    model.eval()

    fig, axes = plt.subplots(2, 7, figsize=(20, 6))
    titles = ["Image A (0.5m)", "Image B (0.5m)", "Ground Truth", "Pred Mask (0.5m)", 
              "Image A (10m)", "Image B (10m)", "Pred Mask (10m)"]
    
    for c in range(7):
        axes[0, c].set_title(titles[c])
    
    for row, filename in enumerate(filenames):
        path_a = os.path.join("dataset/test/A", filename)
        path_b = os.path.join("dataset/test/B", filename)
        path_label = os.path.join("dataset/test/label", filename)
        
        img_a = np.array(Image.open(path_a).convert("RGB"))
        img_b = np.array(Image.open(path_b).convert("RGB"))
        label = np.array(Image.open(path_label).convert("L"))
        gt_mask = (label > 0).astype(np.uint8)
        
        if img_a.shape[:2] != (256, 256):
            img_a = np.array(Image.fromarray(img_a).resize((256, 256), resample=Image.LANCZOS))
            img_b = np.array(Image.fromarray(img_b).resize((256, 256), resample=Image.LANCZOS))
            gt_mask = np.array(Image.fromarray(gt_mask).resize((256, 256), resample=Image.NEAREST))
            
        # 20x degraded
        deg20_a = degrade_image(img_a, 20)
        deg20_b = degrade_image(img_b, 20)
        
        # Inference 1x
        in1_a = preprocess_numpy(img_a)
        in1_b = preprocess_numpy(img_b)
        # Inference 20x
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
        
        display_items = [img_a, img_b, gt_mask*255, pred1*255, deg20_a, deg20_b, pred20*255]
        for col, item in enumerate(display_items):
            axes[row, col].imshow(item, cmap='gray' if len(item.shape)==2 else None)
            axes[row, col].axis('off')
            
    plt.tight_layout()
    plt.savefig('visual_degradation_proof.png', dpi=150, bbox_inches='tight')
    print("Saved visual_degradation_proof.png")

if __name__ == "__main__":
    run()
