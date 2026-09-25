"""
Analyze degradation results to understand the actual failure mode:
- What fraction of 10m predictions are blank vs blobby vs accurate?
- How does prediction area/shape change across degradation levels?
"""
import pandas as pd
import numpy as np

df = pd.read_csv('degradation_results.csv')

factors = [1, 2, 4, 8, 16, 20]
resolutions = {1: "0.5m", 2: "1.0m", 4: "2.0m", 8: "4.0m", 16: "8.0m", 20: "10.0m"}

# Only look at images that have actual ground truth change (tp+fn > 0 at 1x)
df_1x = df[df['factor'] == 1]
has_change = df_1x[df_1x['tp'] + df_1x['fn'] > 0]['image'].values
print(f"Images with ground truth change: {len(has_change)} / {len(df_1x)}")

# For images WITHOUT ground truth change, check false positives
no_change = df_1x[df_1x['tp'] + df_1x['fn'] == 0]['image'].values
print(f"Images with NO ground truth change: {len(no_change)}")

for factor in factors:
    res = resolutions[factor]
    df_f = df[df['factor'] == factor]
    
    # Among images WITH change
    df_change = df_f[df_f['image'].isin(has_change)]
    
    # Categorize predictions
    blank = len(df_change[(df_change['tp'] == 0) & (df_change['fp'] == 0)])  # No prediction at all
    near_blank = len(df_change[(df_change['tp'] + df_change['fp'] > 0) & (df_change['tp'] + df_change['fp'] < 100)])
    has_pred = len(df_change[df_change['tp'] + df_change['fp'] >= 100])
    
    total_pred_pixels = (df_change['tp'] + df_change['fp']).sum()
    total_gt_pixels = (df_change['tp'] + df_change['fn']).sum()
    
    # IoU distribution
    ious = df_change['iou']
    good = len(df_change[df_change['iou'] >= 0.5])
    moderate = len(df_change[(df_change['iou'] >= 0.1) & (df_change['iou'] < 0.5)])
    poor = len(df_change[(df_change['iou'] > 0) & (df_change['iou'] < 0.1)])
    zero = len(df_change[df_change['iou'] == 0])
    
    # Precision/recall stats
    avg_prec = df_change['precision'].mean()
    avg_rec = df_change['recall'].mean()
    
    print(f"\n{'='*60}")
    print(f"Factor {factor}x ({res}) — {len(df_change)} images with GT change")
    print(f"  Prediction volume: {total_pred_pixels:,} predicted px vs {total_gt_pixels:,} GT px (ratio: {total_pred_pixels/total_gt_pixels:.2f}x)")
    print(f"  Blank masks (0 predicted px):    {blank} ({100*blank/len(df_change):.1f}%)")
    print(f"  Near-blank (<100 predicted px):   {near_blank} ({100*near_blank/len(df_change):.1f}%)")
    print(f"  Substantive (>=100 predicted px): {has_pred} ({100*has_pred/len(df_change):.1f}%)")
    print(f"  IoU >= 0.5 (good):    {good} ({100*good/len(df_change):.1f}%)")
    print(f"  IoU 0.1-0.5 (moderate): {moderate} ({100*moderate/len(df_change):.1f}%)")
    print(f"  IoU < 0.1 (poor):     {poor} ({100*poor/len(df_change):.1f}%)")
    print(f"  IoU = 0 (miss):       {zero} ({100*zero/len(df_change):.1f}%)")
    print(f"  Mean Precision: {avg_prec:.4f} | Mean Recall: {avg_rec:.4f}")
    
    # Among images WITHOUT change — false positive analysis
    df_nochange = df_f[df_f['image'].isin(no_change)]
    fp_images = len(df_nochange[df_nochange['fp'] > 0])
    total_fp = df_nochange['fp'].sum()
    print(f"  [No-change images] False positive images: {fp_images}/{len(df_nochange)} | Total FP pixels: {total_fp:,}")
