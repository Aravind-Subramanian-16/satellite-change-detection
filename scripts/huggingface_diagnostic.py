import sys

try:
    from huggingface_hub import snapshot_download
    print("huggingface_hub imported successfully.")
    
    # Try downloading with a short timeout (e.g., using max_workers=1 and only allowing small files like json or md)
    path = snapshot_download(repo_id="mnist", repo_type="dataset", allow_patterns="*.json", max_workers=1)
    print(f"Download successful, path: {path}")
except Exception as e:
    print(f"Hugging Face download failed: {e}")

try:
    import torch
    mps_available = torch.backends.mps.is_available()
    print(f"MPS Available: {mps_available}")
except Exception as e:
    print(f"Torch failed: {e}")
