import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

class Fusion3D(nn.Module):
    """
    3D Convolution fusion module inspired by AFCF3D-Net.
    Fuses temporal features (t=2) using a 3D convolution to capture spatial-temporal relations.
    """
    def __init__(self, channels):
        super(Fusion3D, self).__init__()
        # Depthwise 3D Conv (groups=channels) to drastically save parameters
        self.conv3d = nn.Conv3d(channels, channels, kernel_size=(2, 3, 3), padding=(0, 1, 1), groups=channels)
        # Pointwise Conv to mix channels after spatial/temporal fusion
        self.pointwise = nn.Conv2d(channels, channels, kernel_size=1)
        
        self.bn = nn.BatchNorm2d(channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, f1, f2):
        # f1, f2 shape: [B, C, H, W]
        # Stack along temporal dimension: [B, C, 2, H, W]
        x = torch.stack((f1, f2), dim=2)
        
        # 3D Conv: [B, C, 1, H, W]
        x = self.conv3d(x)
        
        # Squeeze temporal dimension: [B, C, H, W]
        x = x.squeeze(2)
        
        # Pointwise mix
        x = self.pointwise(x)
        
        x = self.bn(x)
        x = self.relu(x)
        return x

class DoubleConv(nn.Module):
    """(convolution => [BN] => ReLU) * 2"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)

class Up(nn.Module):
    """Upscaling then double conv"""
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        # Pad if sizes don't match
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]

        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2,
                        diffY // 2, diffY - diffY // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)

class MobileNetV2_3D_CDNet(nn.Module):
    """
    Advanced Change Detection architecture:
    - MobileNetV2 backbone (shared weights)
    - 3D Convolution Fusion (AFCF3D-Net inspired)
    - U-Net style decoder
    """
    def __init__(self, n_classes=1):
        super(MobileNetV2_3D_CDNet, self).__init__()
        
        # Pretrained MobileNetV2 backbone
        import ssl
        _orig_ctx = ssl._create_default_https_context
        try:
            ssl._create_default_https_context = ssl._create_unverified_context  # type: ignore[assignment]
            mobilenet = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT).features
        except Exception:
            mobilenet = models.mobilenet_v2(pretrained=True).features
        finally:
            ssl._create_default_https_context = _orig_ctx
            
        # MobileNetV2 feature extractor
        self.inc = nn.Sequential(*mobilenet[:2])     # 1/2, 16 channels
        self.down1 = nn.Sequential(*mobilenet[2:4])  # 1/4, 24 channels
        self.down2 = nn.Sequential(*mobilenet[4:7])  # 1/8, 32 channels
        self.down3 = nn.Sequential(*mobilenet[7:14]) # 1/16, 96 channels
        self.down4 = nn.Sequential(*mobilenet[14:])  # 1/32, 1280 channels
        
        # 3D Fusion modules at each scale
        self.fuse1 = Fusion3D(16)
        self.fuse2 = Fusion3D(24)
        self.fuse3 = Fusion3D(32)
        self.fuse4 = Fusion3D(96)
        self.fuse5 = Fusion3D(1280)
        
        # Decoder
        self.up1 = Up(1280 + 96, 256)
        self.up2 = Up(256 + 32, 128)
        self.up3 = Up(128 + 24, 64)
        self.up4 = Up(64 + 16, 32)
        
        # Final upsampling to original size (since inc is 1/2)
        self.up5 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            DoubleConv(32, 16)
        )
        
        self.outc = nn.Conv2d(16, n_classes, kernel_size=1)

    def forward_encoder(self, x):
        x1 = self.inc(x)      
        x2 = self.down1(x1)   
        x3 = self.down2(x2)   
        x4 = self.down3(x3)   
        x5 = self.down4(x4)   
        return x1, x2, x3, x4, x5

    def forward(self, x_a, x_b):
        a1, a2, a3, a4, a5 = self.forward_encoder(x_a)
        b1, b2, b3, b4, b5 = self.forward_encoder(x_b)
        
        # 3D Fusion
        f1 = self.fuse1(a1, b1)
        f2 = self.fuse2(a2, b2)
        f3 = self.fuse3(a3, b3)
        f4 = self.fuse4(a4, b4)
        f5 = self.fuse5(a5, b5)
        
        # Decoder
        x = self.up1(f5, f4)
        x = self.up2(x, f3)
        x = self.up3(x, f2)
        x = self.up4(x, f1)
        
        x = self.up5(x)
        logits = self.outc(x)
        return logits
