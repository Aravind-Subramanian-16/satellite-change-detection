import os
import sys
from PIL import Image
import numpy as np
from tqdm import tqdm
import traceback
import matplotlib.pyplot as plt

def crop_and_save(img_path, save_dir, filename, patch_size=256):
    try:
        img = Image.open(img_path)
        w, h = img.size
        name, ext = os.path.splitext(filename)
        if ext == '':
            ext = '.png'
            
        if w == patch_size and h == patch_size:
            patch_name = f"{name}{ext}"
            img.save(os.path.join(save_dir, patch_name))
            return

        for i in range(0, h, patch_size):
            for j in range(0, w, patch_size):
                box = (j, i, j + patch_size, i + patch_size)
                patch = img.crop(box)
                
                if patch.size == (patch_size, patch_size):
                    patch_name = f"{name}_{i}_{j}{ext}"
                    patch.save(os.path.join(save_dir, patch_name))
    except Exception as e:
        print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    src_dir = "/Volumes/My Passport/LEVIR-CD 2"
    dest_dir = "dataset"
    
    if os.path.exists(dest_dir):
        import shutil
        shutil.rmtree(dest_dir)
        
    for split in ['train', 'val', 'test']:
        for subdir in ['A', 'B', 'label']:
            os.makedirs(os.path.join(dest_dir, split, subdir), exist_ok=True)
            
        split_path = os.path.join(src_dir, split)
        if not os.path.exists(split_path):
            continue
            
        print(f"Processing {split} split...")
        files = os.listdir(os.path.join(split_path, 'A'))
        files = [f for f in files if f.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff'))]
        
        for filename in tqdm(files):
            img_a = os.path.join(split_path, 'A', filename)
            img_b = os.path.join(split_path, 'B', filename)
            label = os.path.join(split_path, 'label', filename)
            
            crop_and_save(img_a, os.path.join(dest_dir, split, 'A'), filename)
            crop_and_save(img_b, os.path.join(dest_dir, split, 'B'), filename)
            crop_and_save(label, os.path.join(dest_dir, split, 'label'), filename)
            
    print("Done generating patches.")
    
    # Generate 3 real triplets
    import random
    train_a_dir = os.path.join(dest_dir, 'train', 'A')
    train_b_dir = os.path.join(dest_dir, 'train', 'B')
    train_l_dir = os.path.join(dest_dir, 'train', 'label')
    
    patches = os.listdir(train_a_dir)
    random.shuffle(patches)
    selected_patches = patches[:3]
    
    fig, axes = plt.subplots(3, 3, figsize=(12, 12))
    for i, patch_name in enumerate(selected_patches):
        img_a = Image.open(os.path.join(train_a_dir, patch_name))
        img_b = Image.open(os.path.join(train_b_dir, patch_name))
        label = Image.open(os.path.join(train_l_dir, patch_name))
        
        axes[i, 0].imshow(img_a)
        axes[i, 0].set_title(f"Before - {patch_name}")
        axes[i, 0].axis('off')
        
        axes[i, 1].imshow(img_b)
        axes[i, 1].set_title(f"After - {patch_name}")
        axes[i, 1].axis('off')
        
        axes[i, 2].imshow(label, cmap='gray')
        axes[i, 2].set_title(f"Label - {patch_name}")
        axes[i, 2].axis('off')
        
    plt.tight_layout()
    plt.savefig('dataset_samples_local.png')
    print("Saved 3 sample triplets to dataset_samples_local.png")
