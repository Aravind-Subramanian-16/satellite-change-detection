import os
import io
import shutil
import pandas as pd
from PIL import Image
from huggingface_hub import snapshot_download

artifact_dir = "/Users/aravind/.gemini/antigravity-ide/brain/8771064e-34ac-407d-b6a3-d3803393ad41"

def print_tree(d, indent=""):
    items = sorted(os.listdir(d))
    for i, item in enumerate(items):
        path = os.path.join(d, item)
        is_last = (i == len(items) - 1)
        prefix = "└── " if is_last else "├── "
        print(f"{indent}{prefix}{item}")
        if os.path.isdir(path):
            print_tree(path, indent + ("    " if is_last else "│   "))

print("Attempting snapshot_download for snchen1230/LEVIRCDPlus...")
try:
    path = snapshot_download(repo_id="snchen1230/LEVIRCDPlus", repo_type="dataset", allow_patterns=["*.parquet", "*.bin", "*.jpg", "*.png", "*.json"])
    print("\nsnchen1230/LEVIRCDPlus directory structure:")
    print_tree(path)
    # Check if there are usable images or just corrupted/unreadable chunks
    valid = any(f.endswith('.parquet') or f.endswith('.png') or f.endswith('.jpg') for root, _, files in os.walk(path) for f in files)
    if not valid:
        print("Repo only contains corrupted or unreadable raw chunk/bin files without parquet structure.")
        raise ValueError("Corrupted raw files.")
except Exception as e:
    print(f"\nsnchen1230/LEVIRCDPlus failed: {e}")
    print("\nFalling back to ericyu/LEVIRCD_Cropped_256...")
    
    path = snapshot_download(repo_id="ericyu/LEVIRCD_Cropped_256", repo_type="dataset", allow_patterns=["*.parquet"])
    print("\nericyu/LEVIRCD_Cropped_256 directory structure:")
    print_tree(path)
    
    # Process parquet files to extract the first 3 images
    # We will use the test split parquet
    parquet_files = [os.path.join(root, f) for root, _, files in os.walk(path) for f in files if f.endswith('.parquet') and 'test' in f]
    if parquet_files:
        df = pd.read_parquet(parquet_files[0])
        print(f"\nExtracted {len(df)} rows from {os.path.basename(parquet_files[0])}")
        
        # Save 3 sample pairs
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            # Huggingface dataset parquet stores images as {'bytes': b'...', 'path': None}
            img_a = Image.open(io.BytesIO(row['image_A']['bytes']))
            img_b = Image.open(io.BytesIO(row['image_B']['bytes']))
            label = Image.open(io.BytesIO(row['label']['bytes']))
            
            img_a.save(os.path.join(artifact_dir, f"real_sample_{i}_A.png"))
            img_b.save(os.path.join(artifact_dir, f"real_sample_{i}_B.png"))
            label.save(os.path.join(artifact_dir, f"real_sample_{i}_label.png"))
        print("\nSaved 3 real sample pairs to artifacts.")
        
        # Calculate size on disk
        total_size = sum(os.path.getsize(os.path.join(dirpath, f)) for dirpath, _, filenames in os.walk(path) for f in filenames)
        print(f"\nTotal dataset size on disk: {total_size / (1024**3):.2f} GB")
        
