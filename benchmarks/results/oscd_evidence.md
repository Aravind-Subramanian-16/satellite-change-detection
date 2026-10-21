# OSCD evidence from saved v2 results

Generated: 2026-10-21  
Source: `/Volumes/My Passport/Projects/Mini Project/satellite-change-detection/benchmarks/results/oscd_results_v2.json` (SHA-256 `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f`, 52665 bytes)  
Scope: saved per-city test confusion counts only; no re-scoring

## Pooled test results

The random baseline is the analytic expectation for a predictor that marks each pixel changed with probability equal to the true change fraction. The all-no-change predictor has F1 = 0 by definition.

| Method | True change % | Predicted % | Precision | Recall | F1 | IoU | OA | All-no-change F1 | Random expected F1 | F1 - random |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Hardcoded NDVI/NDBI | 5.17 | 2.24 | 0.1292 | 0.0561 | 0.0782 | 0.0407 | 0.9317 | 0.0000 | 0.0517 | +0.0265 |
| Percentile 99.0 | 5.17 | 1.66 | 0.2419 | 0.0777 | 0.1176 | 0.0625 | 0.9397 | 0.0000 | 0.0517 | +0.0659 |
| Otsu | 5.17 | 67.35 | 0.0513 | 0.6684 | 0.0953 | 0.0500 | 0.3439 | 0.0000 | 0.0517 | +0.0436 |
| CNN joint-percentile | 5.17 | 0.01 | 0.2983 | 0.0003 | 0.0007 | 0.0003 | 0.9483 | 0.0000 | 0.0517 | -0.0510 |
| CNN reflectance | 5.17 | 0.00 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9483 | 0.0000 | 0.0517 | -0.0517 |

## Per-city results

Each method uses the same ten test cities and the same labels. `Random F1` is the expected F1 at that city's true change fraction.

### Hardcoded NDVI/NDBI

| City | True change % | Predicted % | F1 | IoU | Random F1 | F1 - random |
|---|---:|---:|---:|---:|---:|---:|
| brasilia | 2.58 | 0.32 | 0.0590 | 0.0304 | 0.0258 | +0.0332 |
| chongqing | 7.21 | 1.91 | 0.3102 | 0.1836 | 0.0721 | +0.2381 |
| dubai | 9.92 | 0.05 | 0.0032 | 0.0016 | 0.0992 | -0.0960 |
| lasvegas | 7.67 | 0.27 | 0.0533 | 0.0274 | 0.0767 | -0.0234 |
| milano | 0.80 | 0.42 | 0.1133 | 0.0600 | 0.0080 | +0.1053 |
| montpellier | 6.79 | 1.10 | 0.0355 | 0.0180 | 0.0679 | -0.0325 |
| norcia | 1.32 | 5.14 | 0.0350 | 0.0178 | 0.0132 | +0.0218 |
| rio | 5.69 | 2.51 | 0.1755 | 0.0962 | 0.0569 | +0.1186 |
| saclay_w | 1.14 | 9.88 | 0.0045 | 0.0022 | 0.0114 | -0.0070 |
| valencia | 0.44 | 1.69 | 0.0133 | 0.0067 | 0.0044 | +0.0089 |

### Percentile 99.0

| City | True change % | Predicted % | F1 | IoU | Random F1 | F1 - random |
|---|---:|---:|---:|---:|---:|---:|
| brasilia | 2.58 | 1.66 | 0.1082 | 0.0572 | 0.0258 | +0.0824 |
| chongqing | 7.21 | 1.74 | 0.2481 | 0.1416 | 0.0721 | +0.1760 |
| dubai | 9.92 | 1.72 | 0.0500 | 0.0257 | 0.0992 | -0.0492 |
| lasvegas | 7.67 | 1.74 | 0.1548 | 0.0839 | 0.0767 | +0.0780 |
| milano | 0.80 | 1.72 | 0.1219 | 0.0649 | 0.0080 | +0.1140 |
| montpellier | 6.79 | 1.67 | 0.0490 | 0.0251 | 0.0679 | -0.0190 |
| norcia | 1.32 | 1.37 | 0.0345 | 0.0175 | 0.0132 | +0.0212 |
| rio | 5.69 | 1.68 | 0.1482 | 0.0800 | 0.0569 | +0.0913 |
| saclay_w | 1.14 | 1.56 | 0.0005 | 0.0003 | 0.0114 | -0.0109 |
| valencia | 0.44 | 1.40 | 0.0134 | 0.0068 | 0.0044 | +0.0090 |

### Otsu

| City | True change % | Predicted % | F1 | IoU | Random F1 | F1 - random |
|---|---:|---:|---:|---:|---:|---:|
| brasilia | 2.58 | 69.31 | 0.0640 | 0.0331 | 0.0258 | +0.0382 |
| chongqing | 7.21 | 53.58 | 0.1497 | 0.0809 | 0.0721 | +0.0776 |
| dubai | 9.92 | 79.13 | 0.1379 | 0.0740 | 0.0992 | +0.0387 |
| lasvegas | 7.67 | 80.71 | 0.1327 | 0.0711 | 0.0767 | +0.0559 |
| milano | 0.80 | 67.84 | 0.0167 | 0.0084 | 0.0080 | +0.0088 |
| montpellier | 6.79 | 57.13 | 0.1418 | 0.0763 | 0.0679 | +0.0738 |
| norcia | 1.32 | 72.75 | 0.0348 | 0.0177 | 0.0132 | +0.0215 |
| rio | 5.69 | 57.09 | 0.0796 | 0.0415 | 0.0569 | +0.0228 |
| saclay_w | 1.14 | 48.90 | 0.0240 | 0.0121 | 0.0114 | +0.0126 |
| valencia | 0.44 | 78.25 | 0.0095 | 0.0048 | 0.0044 | +0.0051 |

### CNN joint-percentile

| City | True change % | Predicted % | F1 | IoU | Random F1 | F1 - random |
|---|---:|---:|---:|---:|---:|---:|
| brasilia | 2.58 | 0.00 | 0.0000 | 0.0000 | 0.0258 | -0.0258 |
| chongqing | 7.21 | 0.00 | 0.0000 | 0.0000 | 0.0721 | -0.0721 |
| dubai | 9.92 | 0.00 | 0.0000 | 0.0000 | 0.0992 | -0.0992 |
| lasvegas | 7.67 | 0.02 | 0.0024 | 0.0012 | 0.0767 | -0.0744 |
| milano | 0.80 | 0.00 | 0.0000 | 0.0000 | 0.0080 | -0.0080 |
| montpellier | 6.79 | 0.00 | 0.0000 | 0.0000 | 0.0679 | -0.0679 |
| norcia | 1.32 | 0.00 | 0.0000 | 0.0000 | 0.0132 | -0.0132 |
| rio | 5.69 | 0.00 | 0.0000 | 0.0000 | 0.0569 | -0.0569 |
| saclay_w | 1.14 | 0.00 | 0.0000 | 0.0000 | 0.0114 | -0.0114 |
| valencia | 0.44 | 0.02 | 0.0000 | 0.0000 | 0.0044 | -0.0044 |

### CNN reflectance

| City | True change % | Predicted % | F1 | IoU | Random F1 | F1 - random |
|---|---:|---:|---:|---:|---:|---:|
| brasilia | 2.58 | 0.00 | 0.0000 | 0.0000 | 0.0258 | -0.0258 |
| chongqing | 7.21 | 0.00 | 0.0000 | 0.0000 | 0.0721 | -0.0721 |
| dubai | 9.92 | 0.00 | 0.0000 | 0.0000 | 0.0992 | -0.0992 |
| lasvegas | 7.67 | 0.00 | 0.0000 | 0.0000 | 0.0767 | -0.0767 |
| milano | 0.80 | 0.00 | 0.0000 | 0.0000 | 0.0080 | -0.0080 |
| montpellier | 6.79 | 0.00 | 0.0000 | 0.0000 | 0.0679 | -0.0679 |
| norcia | 1.32 | 0.00 | 0.0000 | 0.0000 | 0.0132 | -0.0132 |
| rio | 5.69 | 0.00 | 0.0000 | 0.0000 | 0.0569 | -0.0569 |
| saclay_w | 1.14 | 0.00 | 0.0000 | 0.0000 | 0.0114 | -0.0114 |
| valencia | 0.44 | 0.00 | 0.0000 | 0.0000 | 0.0044 | -0.0044 |

## City-level bootstrap

Seed 0; 10,000 resamples of the 10 cities with replacement; percentile 2.5-97.5 percentile intervals. Intervals reflect city sampling only.

| Method | F1 | F1 95% CI | IoU | IoU 95% CI | Delta F1 vs hardcoded | Delta F1 95% CI | P(Delta F1 > 0) |
|---|---:|---|---:|---|---:|---|---:|
| Hardcoded NDVI/NDBI | 0.0782 | [0.0168, 0.1846] | 0.0407 | [0.0085, 0.1017] | reference | - | - |
| Percentile 99.0 | 0.1176 | [0.0540, 0.1802] | 0.0625 | [0.0277, 0.0990] | +0.0394 | [-0.0176, +0.0778] | 0.931 |
| Otsu | 0.0953 | [0.0495, 0.1245] | 0.0500 | [0.0254, 0.0664] | +0.0171 | [-0.0941, +0.0829] | 0.651 |
| CNN joint-percentile | 0.0007 | [0.0000, 0.0017] | 0.0003 | [0.0000, 0.0009] | -0.0775 | [-0.1844, -0.0164] | 0.000 |
| CNN reflectance | 0.0000 | [0.0000, 0.0000] | 0.0000 | [0.0000, 0.0000] | -0.0782 | [-0.1846, -0.0168] | 0.000 |

## Failure analysis

### Correlations across ten cities

| Method | Pearson r (true fraction, F1) | Spearman rho | Pearson r (true fraction, predicted fraction) |
|---|---:|---:|---:|
| Hardcoded NDVI/NDBI | 0.237 | 0.079 | -0.455 |
| Percentile 99.0 | 0.426 | 0.552 | 0.662 |
| Otsu | 0.951 | 0.903 | 0.075 |
| CNN joint-percentile | 0.336 | 0.406 | 0.018 |
| CNN reflectance | undefined (constant) | undefined (constant) | undefined (constant) |

These are descriptive statistics for ten cities; they do not identify a cause.

### Prediction balance

| Method | Cities under true fraction | Cities over true fraction | Cities equal |
|---|---|---|---|
| Hardcoded NDVI/NDBI | 7 (brasilia, chongqing, dubai, lasvegas, milano, montpellier, rio) | 3 (norcia, saclay_w, valencia) | 0 |
| Percentile 99.0 | 6 (brasilia, chongqing, dubai, lasvegas, montpellier, rio) | 4 (milano, norcia, saclay_w, valencia) | 0 |
| Otsu | 0 (none) | 10 (brasilia, chongqing, dubai, lasvegas, milano, montpellier, norcia, rio, saclay_w, valencia) | 0 |
| CNN joint-percentile | 10 (brasilia, chongqing, dubai, lasvegas, milano, montpellier, norcia, rio, saclay_w, valencia) | 0 (none) | 0 |
| CNN reflectance | 10 (brasilia, chongqing, dubai, lasvegas, milano, montpellier, norcia, rio, saclay_w, valencia) | 0 (none) | 0 |

### CNN and Otsu observations

- CNN joint-percentile predicted zero change pixels in 8 of 10 cities: brasilia, montpellier, norcia, rio, saclay_w, dubai, milano, chongqing.
- CNN reflectance predicted zero change pixels in 10 of 10 cities.
- Otsu predicted more than the true change fraction in 10 of 10 cities; pooled predicted fraction 67.35% versus 5.17% true; pooled precision 0.0513, recall 0.6684, OA 0.3439.
- Otsu predicted fraction ranges from 48.90% to 80.71% across cities.

The Otsu result is consistent with its per-city thresholds marking a large share of pixels changed; the saved data support the prediction-volume explanation, not a causal account.

## Pipeline specification

Read from code, not inferred:

- OSCD bands read: B02, B03, B04, B08, B11.
- NDVI: `(B08 - B04) / max(B08 + B04, 1e-6)`; NDBI: `(B11 - B08) / max(B11 + B08, 1e-6)`; differences are after minus before.
- CNN RGB input: B04, B03, B02. Reflectance: `clip(raw / 10000 * 255, 0, 255) as uint8`. Joint percentile: 2nd and 98th percentiles over both dates combined; clip((raw - low) * 255 / (high - low), 0, 255).
- Tiling: 256x256 tiles, 32-pixel overlap, edge padding, averaged probabilities; scene resize: False; threshold 0.5.
- Degradation: PIL ImageFilter.GaussianBlur(radius=factor/2); no explicit kernel size; downsample PIL LANCZOS to (width // factor, height // factor); upsample PIL LANCZOS back to 256x256; threshold 0.5.

| Factor | Target resolution | Blur radius (px) | Intermediate size |
|---:|---:|---:|---:|
| 1 | 0.5 m | 0 | 256x256 |
| 2 | 1 m | 1.0 | 128x128 |
| 4 | 2 m | 2.0 | 64x64 |
| 8 | 4 m | 4.0 | 32x32 |
| 16 | 8 m | 8.0 | 16x16 |
| 20 | 10 m | 10.0 | 12x12 |

- Metric aggregation: pooled TP/FP/FN/TN (micro), not mean of per-image metrics.

Code references: `benchmarks/oscd_eval.py:27-32`, `benchmarks/oscd_eval.py:41-55`, `benchmarks/oscd_eval.py:77-96`, `benchmarks/oscd_eval.py:133-152`, `benchmarks/oscd_eval.py:206-213`, `app.py:366-381`, `tiling.py:6-25`, `evaluate_degradation.py:19-31`, `evaluate_degradation.py:76-116`, `spectral_pipeline.py:63-87`.

## Caveats

- Bootstrap intervals reflect sampling of the ten test cities only.
- Pixel-level and model-training uncertainty are not included.
- The random baseline is an expectation, not a run.
- The CNN reflectance row has no predicted positives in any test city.
- No causal claim is made from the city-level correlations.
