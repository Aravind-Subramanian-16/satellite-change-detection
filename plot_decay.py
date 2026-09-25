import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
df = pd.read_csv('degradation_results.csv')

# Calculate Micro-Averaged F1 and IoU per factor
grouped = df.groupby('factor')[['tp', 'fp', 'fn']].sum()

factors = [1, 2, 4, 8, 16, 20]
resolutions = [0.5, 1.0, 2.0, 4.0, 8.0, 10.0]
f1_scores = []
iou_scores = []

for factor in factors:
    if factor in grouped.index:
        tps = grouped.loc[factor, 'tp']
        fps = grouped.loc[factor, 'fp']
        fns = grouped.loc[factor, 'fn']
        
        micro_prec = tps / (tps + fps) if (tps + fps) > 0 else 0.0
        micro_rec = tps / (tps + fns) if (tps + fns) > 0 else 0.0
        
        f1 = 2 * (micro_prec * micro_rec) / (micro_prec + micro_rec) if (micro_prec + micro_rec) > 0 else 0.0
        iou = tps / (tps + fps + fns) if (tps + fps + fns) > 0 else 0.0
        
        f1_scores.append(f1)
        iou_scores.append(iou)

plt.figure(figsize=(10, 6))

# Plot lines
plt.plot(resolutions, f1_scores, marker='o', linestyle='-', linewidth=2, markersize=8, label='F1 Score', color='#1f77b4')
plt.plot(resolutions, iou_scores, marker='s', linestyle='-', linewidth=2, markersize=8, label='IoU', color='#ff7f0e')

# Formatting
plt.title('Change Detection Performance vs. Spatial Resolution Degradation', fontsize=14, pad=15)
plt.xlabel('Spatial Resolution (meters/pixel)', fontsize=12)
plt.ylabel('Score (0.0 to 1.0)', fontsize=12)

# X-axis ticks
plt.xticks(resolutions, [f"{r}m" for r in resolutions])
plt.ylim(0, 1.0)
plt.grid(True, linestyle='--', alpha=0.6)

# Sentinel-2 line
plt.axvline(x=10.0, color='r', linestyle='--', linewidth=2, alpha=0.8)
plt.text(9.7, 0.5, 'Sentinel-2 resolution (10m)', color='red', rotation=90, 
         verticalalignment='center', fontsize=11, fontweight='bold',
         bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))

# Legend
plt.legend(loc='upper right', fontsize=11)

plt.tight_layout()
plt.savefig('decay_curve.png', dpi=300, bbox_inches='tight')
print("Saved decay_curve.png")
