import os
from PIL import Image
import torch
from torch.utils.data import Dataset
import torchvision.transforms as transforms

class ChangeDetectionDataset(Dataset):
    def __init__(self, data_dir, split='train', transform=None):
        self.split_dir = os.path.join(data_dir, split)
        self.a_dir = os.path.join(self.split_dir, 'A')
        self.b_dir = os.path.join(self.split_dir, 'B')
        self.label_dir = os.path.join(self.split_dir, 'label')
        
        self.filenames = [f for f in os.listdir(self.a_dir) if f.endswith(('.png', '.jpg'))]
        
        if transform is None:
            self.transform = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
        else:
            self.transform = transform

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, index):
        filename = self.filenames[index]
        
        a_path = os.path.join(self.a_dir, filename)
        b_path = os.path.join(self.b_dir, filename)
        label_path = os.path.join(self.label_dir, filename)
        
        img_a = Image.open(a_path).convert('RGB')
        img_b = Image.open(b_path).convert('RGB')
        label = Image.open(label_path).convert('L')
        
        # Basic transformation
        if self.transform:
            img_a = self.transform(img_a)
            img_b = self.transform(img_b)
            
        label = transforms.ToTensor()(label) # returns [0, 1] tensor
        label = (label > 0.5).float() # binarize
        
        return img_a, img_b, label
