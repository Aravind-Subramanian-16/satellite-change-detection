import os
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import time
from torch.utils.data import DataLoader
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm

from dataset import ChangeDetectionDataset
from model import MobileNetV2_3D_CDNet

def calculate_iou(preds, labels):
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

def train():
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

    epochs = 100 # High number to allow early stopping
    batch_size = 4
    lr = 5e-4
    patience_limit = 10

    dataset_dir = 'dataset'

    train_dataset = ChangeDetectionDataset(dataset_dir, split='train')
    val_dataset = ChangeDetectionDataset(dataset_dir, split='val')

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
    print(f"Model parameters: {count_parameters(model) / 1e6:.2f}M")

    # AdamW with Cosine Annealing LR
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs)

    best_iou = 0.0
    patience = 0
    start_time = time.time()

    for epoch in range(epochs):
        model.train()
        train_loss = 0
        train_iou = 0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs} [Train]")
        for img_a, img_b, label in pbar:
            img_a, img_b, label = img_a.to(device), img_b.to(device), label.to(device)

            optimizer.zero_grad()
            outputs = model(img_a, img_b)

            loss = dice_bce_loss(outputs, label)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_iou += calculate_iou(outputs, label)

            pbar.set_postfix({'loss': f"{loss.item():.4f}"})

        scheduler.step()

        avg_train_loss = train_loss / len(train_loader)
        avg_train_iou = train_iou / len(train_loader)

        # Validation
        model.eval()
        val_loss = 0
        val_iou = 0

        with torch.no_grad():
            for img_a, img_b, label in tqdm(val_loader, desc=f"Epoch {epoch+1}/{epochs} [Val]"):
                img_a, img_b, label = img_a.to(device), img_b.to(device), label.to(device)

                outputs = model(img_a, img_b)
                loss = dice_bce_loss(outputs, label)

                val_loss += loss.item()
                val_iou += calculate_iou(outputs, label)

        avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0
        avg_val_iou = val_iou / len(val_loader) if len(val_loader) > 0 else 0

        print(f"Epoch {epoch+1}: Train Loss: {avg_train_loss:.4f}, Train IoU: {avg_train_iou:.4f} | Val Loss: {avg_val_loss:.4f}, Val IoU: {avg_val_iou:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}")

        if avg_val_iou >= best_iou:
            best_iou = avg_val_iou
            torch.save(model.state_dict(), 'best_model.pt')
            print("Saved new best model.")
            patience = 0
        else:
            patience += 1
            print(f"Validation IoU did not improve. Patience: {patience}/{patience_limit}")

        if patience >= patience_limit:
            print(f"Early stopping triggered after {epoch+1} epochs.")
            break

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Training completed in {total_time:.2f} seconds ({total_time/3600:.2f} hours).")
    print(f"Best Validation IoU: {best_iou:.4f}")

if __name__ == "__main__":
    train()
