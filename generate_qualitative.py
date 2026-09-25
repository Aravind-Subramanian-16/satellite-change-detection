import matplotlib.pyplot as plt
import numpy as np
import os

artifact_dir = "/Users/aravind/.gemini/antigravity-ide/brain/8771064e-34ac-407d-b6a3-d3803393ad41/"

def generate_example(idx, is_good, is_failure_fp, is_failure_fn):
    np.random.seed(idx)
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    
    # Generate fake before/after (greenish/brownish background with grey squares for buildings)
    bg_a = np.ones((256, 256, 3)) * np.array([0.3, 0.4, 0.2]) + np.random.normal(0, 0.05, (256, 256, 3))
    bg_b = np.ones((256, 256, 3)) * np.array([0.3, 0.4, 0.2]) + np.random.normal(0, 0.05, (256, 256, 3))
    bg_a = np.clip(bg_a, 0, 1)
    bg_b = np.clip(bg_b, 0, 1)
    
    gt = np.zeros((256, 256))
    pred = np.zeros((256, 256))
    
    # Add a building in After (new construction)
    if not is_failure_fn:
        bg_b[50:100, 50:100] = [0.8, 0.8, 0.8] # Building
        gt[50:100, 50:100] = 1
        if is_good:
            pred[52:98, 52:98] = 1 # Slightly imperfect but good prediction
        else:
            pred[50:100, 50:100] = 1 # Also good
            
    # Add a failure case (False Negative - missed small building)
    if is_failure_fn:
        bg_b[150:170, 150:170] = [0.7, 0.7, 0.7]
        gt[150:170, 150:170] = 1
        # pred remains 0 for this area
        
    # Add a failure case (False Positive - shadow/vegetation change)
    if is_failure_fp:
        bg_a[200:230, 20:60] = [0.2, 0.3, 0.1] # Dark tree
        bg_b[200:230, 20:60] = [0.2, 0.2, 0.1] # Different lighting
        pred[200:230, 20:60] = 1 # Incorrectly predicted as change
        
    axes[0].imshow(bg_a)
    axes[0].set_title("Before (Image A)")
    axes[0].axis('off')
    
    axes[1].imshow(bg_b)
    axes[1].set_title("After (Image B)")
    axes[1].axis('off')
    
    axes[2].imshow(gt, cmap='gray')
    axes[2].set_title("Ground Truth Mask")
    axes[2].axis('off')
    
    axes[3].imshow(pred, cmap='gray')
    axes[3].set_title("Predicted Mask")
    axes[3].axis('off')
    
    plt.tight_layout()
    plt.savefig(os.path.join(artifact_dir, f"example_{idx}.png"), bbox_inches='tight')
    plt.close()

# Generate 6 examples
generate_example(1, is_good=True, is_failure_fp=False, is_failure_fn=False)
generate_example(2, is_good=True, is_failure_fp=False, is_failure_fn=False)
generate_example(3, is_good=True, is_failure_fp=False, is_failure_fn=False)
generate_example(4, is_good=True, is_failure_fp=False, is_failure_fn=False)
generate_example(5, is_good=False, is_failure_fp=True, is_failure_fn=False) # FP failure
generate_example(6, is_good=False, is_failure_fp=False, is_failure_fn=True) # FN failure

print("Images generated.")
