import os
from pathlib import Path
import torch
from torch.utils.data import DataLoader
from dataset import ChangeDetectionDataset
from model import MobileNetV2_3D_CDNet
from tqdm import tqdm

def evaluate():
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
    print(f"Evaluating on device: {device}")
    
    dataset_dir = 'dataset'
    test_dataset = ChangeDetectionDataset(dataset_dir, split='test')
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False)
    
    model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
    
    checkpoint_path = Path(os.environ.get("MODEL_PT_PATH", "best_model.pt"))
    try:
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))
        print(f"Loaded {checkpoint_path}")
    except FileNotFoundError:
        print(f"No checkpoint at {checkpoint_path}. Set MODEL_PT_PATH or train the model.")
        return

    model.eval()
    
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0
    
    with torch.no_grad():
        for img_a, img_b, label in tqdm(test_loader, desc="Evaluating"):
            img_a, img_b, label = img_a.to(device), img_b.to(device), label.to(device)
            
            outputs = model(img_a, img_b)
            preds = (torch.sigmoid(outputs) > 0.5).float()
            
            # Flatten
            preds = preds.view(-1)
            label = label.view(-1)
            
            tp = (preds * label).sum().item()
            fp = (preds * (1 - label)).sum().item()
            fn = ((1 - preds) * label).sum().item()
            tn = ((1 - preds) * (1 - label)).sum().item()
            
            total_tp += tp
            total_fp += fp
            total_fn += fn
            total_tn += tn
            
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    iou = total_tp / (total_tp + total_fp + total_fn) if (total_tp + total_fp + total_fn) > 0 else 0
    
    print("\n--- Test Results ---")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"IoU:       {iou:.4f}")

if __name__ == "__main__":
    evaluate()
