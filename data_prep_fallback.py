import os
import io
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

print("\nDownloading ericyu/LEVIRCD_Cropped_256...")
try:
    path = snapshot_download(repo_id="ericyu/LEVIRCD_Cropped_256", repo_type="dataset", allow_patterns=["*.parquet"])
    print("\nericyu/LEVIRCD_Cropped_256 directory structure:")
    print_tree(path)
    
    # Process parquet files to extract the first 3 images
    parquet_files = [os.path.join(root, f) for root, _, files in os.walk(path) for f in files if f.endswith('.parquet') and 'test' in f]
    if parquet_files:
        df = pd.read_parquet(parquet_files[0])
        print(f"\nExtracted {len(df)} rows from {os.path.basename(parquet_files[0])}")
        
        # Save 3 sample pairs
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            img_a = Image.open(io.BytesIO(row['image_A']['bytes']))
            img_b = Image.open(io.BytesIO(row['image_B']['bytes']))
            label = Image.open(io.BytesIO(row['label']['bytes']))
            
            img_a.save(os.path.join(artifact_dir, f"real_sample_{i}_A.png"))
            img_b.save(os.path.join(artifact_dir, f"real_sample_{i}_B.png"))
            label.save(os.path.join(artifact_dir, f"real_sample_{i}_label.png"))
        print("\nSaved 3 real sample pairs to artifacts.")
        
        total_size = sum(os.path.getsize(os.path.join(dirpath, f)) for dirpath, _, filenames in os.walk(path) for f in filenames)
        print(f"\nTotal dataset size on disk: {total_size / (1024**3):.2f} GB")
except Exception as e:
    print(f"Error: {e}")
