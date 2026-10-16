import os
import torch
from model import MobileNetV2_3D_CDNet

def export_onnx(model_path=None, onnx_path=None):
    model_path = model_path or os.environ.get("MODEL_PT_PATH", "best_model.pt")
    onnx_path = onnx_path or os.environ.get("MODEL_ONNX_PATH", "model.onnx")
    device = torch.device('cpu') # Export on CPU
    model = MobileNetV2_3D_CDNet(n_classes=1).to(device)
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"Loaded {model_path}")
    except FileNotFoundError:
        print("No best_model.pt found. Have you trained the model?")
        return

    model.eval()

    # Dummy inputs for ONNX tracing
    # Batch size 1, 3 channels, 256x256
    dummy_a = torch.randn(1, 3, 256, 256, device=device)
    dummy_b = torch.randn(1, 3, 256, 256, device=device)

    print(f"Exporting model to {onnx_path}...")
    
    torch.onnx.export(
        model, 
        (dummy_a, dummy_b), 
        onnx_path,
        export_params=True,
        opset_version=14, # 14 is generally stable for recent models
        do_constant_folding=True,
        input_names=['input_a', 'input_b'],
        output_names=['output'],
        dynamic_axes={
            'input_a': {0: 'batch_size'},
            'input_b': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    print("Export complete.")

if __name__ == "__main__":
    export_onnx()
