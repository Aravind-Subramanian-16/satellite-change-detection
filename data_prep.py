import os
import sys
from PIL import Image
import numpy as np
from tqdm import tqdm
import traceback
import matplotlib.pyplot as plt
from datasets import load_dataset

def crop_and_save(img, save_dir, filename, patch_size=256):
    try:
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
                
                # Only save if it's a full patch
                if patch.size == (patch_size, patch_size):
                    patch_name = f"{name}_{i}_{j}{ext}"
                    patch.save(os.path.join(save_dir, patch_name))
    except Exception as e:
        print(f"Error processing {filename}: {e}")

def get_image_keys(sample):
    keys = list(sample.keys())
    # Guess the keys for A, B, and label based on common naming conventions
    a_key = next((k for k in keys if k in ['A', 'image_A', 'image1', 'img1', 'before']), keys[0])
    b_key = next((k for k in keys if k in ['B', 'image_B', 'image2', 'img2', 'after']), keys[1])
    label_key = next((k for k in keys if k in ['label', 'mask', 'change']), keys[2])
    return a_key, b_key, label_key

def verify_and_plot_samples(ds, split_name='train', num_samples=3):
    split_data = ds[split_name]
    a_key, b_key, label_key = get_image_keys(split_data[0])
    
    fig, axes = plt.subplots(num_samples, 3, figsize=(12, 4 * num_samples))
    for i in range(num_samples):
        sample = split_data[i]
        img_a = sample[a_key]
        img_b = sample[b_key]
        label = sample[label_key]
        
        # Plot A
        ax = axes[i, 0] if num_samples > 1 else axes[0]
        ax.imshow(img_a)
        ax.set_title(f"Sample {i} - Before")
        ax.axis('off')
        
        # Plot B
        ax = axes[i, 1] if num_samples > 1 else axes[1]
        ax.imshow(img_b)
        ax.set_title(f"Sample {i} - After")
        ax.axis('off')
        
        # Plot Label
        ax = axes[i, 2] if num_samples > 1 else axes[2]
        ax.imshow(label, cmap='gray')
        ax.set_title(f"Sample {i} - Label")
        ax.axis('off')
        
    plt.tight_layout()
    plt.savefig('dataset_samples.png')
    print("Saved 3 sample triplets to dataset_samples.png")

def download_hf_dataset(dataset_name="snchen1230/LEVIRCDPlus", dest_dir="dataset"):
    try:
        print(f"Downloading dataset {dataset_name} from Hugging Face...")
        ds = load_dataset(dataset_name)
        
        # Print counts
        print("\nDataset Info:")
        for split in ds.keys():
            print(f"  {split}: {len(ds[split])} image pairs")
            
        verify_and_plot_samples(ds, split_name=list(ds.keys())[0], num_samples=3)
        
        a_key, b_key, label_key = get_image_keys(ds[list(ds.keys())[0]][0])
        print(f"\nUsing keys -> Before: '{a_key}', After: '{b_key}', Label: '{label_key}'")
        
        splits = ['train', 'validation', 'test'] if 'validation' in ds else ds.keys()
        
        for split in splits:
            if split not in ds:
                continue
                
            # Map HF split names to our standard ones
            out_split = 'val' if split == 'validation' else split
            
            for subdir in ['A', 'B', 'label']:
                os.makedirs(os.path.join(dest_dir, out_split, subdir), exist_ok=True)
                
            print(f"Processing {split} split...")
            for idx, sample in enumerate(tqdm(ds[split])):
                img_a = sample[a_key]
                img_b = sample[b_key]
                label = sample[label_key]
                
                filename = f"image_{idx}.png"
                
                crop_and_save(img_a, os.path.join(dest_dir, out_split, 'A'), filename)
                crop_and_save(img_b, os.path.join(dest_dir, out_split, 'B'), filename)
                crop_and_save(label, os.path.join(dest_dir, out_split, 'label'), filename)
                
        return True
    except Exception as e:
        print(f"FATAL ERROR: Failed to download or process the dataset '{dataset_name}'.")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    dataset_dir = "dataset"
    
    if os.path.exists(dataset_dir) and len(os.listdir(dataset_dir)) > 0:
        print(f"Dataset directory '{dataset_dir}' already exists. We will remove it to download fresh data.")
        import shutil
        shutil.rmtree(dataset_dir)
        
    download_hf_dataset(dest_dir=dataset_dir)
    print("Done. Ready for training.")
