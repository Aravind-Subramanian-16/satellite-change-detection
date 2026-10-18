# OSCD benchmark results (v2)

The saved v2 test results are the main OSCD result. The official ten-city test split was evaluated with thresholds and CNN preprocessing selected on the 14 training cities only. The hardcoded policy selected from the training search was NDVI drop `-0.30` or NDBI rise `+0.30`; both values are at the search-grid edges. Percentile mode selected `99.0`. For the CNN, `joint_percentile` is marked “chosen on train”; reflectance is the other preprocessing variant. The result JSON records the selected configs and the test rows; it does not retain the CNN's training scores.

The joint-percentile CNN test result is reported as measured: pooled F1 `0.0007` (predicted change `0.01%`, true change `5.17%`). Reflectance has pooled F1 `0.0000`. The CNN's near-empty predictions are visible in its predicted fractions; no accuracy figure is substituted for its F1.

## v2 per-city results

Fractions are shares of pixels, shown as percentages. The score column reports F1 except for Otsu, where it reports overall accuracy (OA). Otsu predicts change for roughly two thirds of all pixels pooled, so its recall is not a useful standalone summary here; use its OA in comparisons.

| City | Method | True change | Predicted change | F1 (Otsu: OA) |
|---|---|---:|---:|---:|
| brasilia | Hardcoded | 2.58% | 0.32% | 0.0590 |
| brasilia | Percentile | 2.58% | 1.66% | 0.1082 |
| brasilia | Otsu | 2.58% | 69.31% | 0.3272 |
| brasilia | CNN joint-percentile (chosen on train) | 2.58% | 0.00% | 0.0000 |
| brasilia | CNN reflectance (other) | 2.58% | 0.00% | 0.0000 |
| montpellier | Hardcoded | 6.79% | 1.10% | 0.0355 |
| montpellier | Percentile | 6.79% | 1.67% | 0.0490 |
| montpellier | Otsu | 6.79% | 57.13% | 0.4514 |
| montpellier | CNN joint-percentile (chosen on train) | 6.79% | 0.00% | 0.0000 |
| montpellier | CNN reflectance (other) | 6.79% | 0.00% | 0.0000 |
| norcia | Hardcoded | 1.32% | 5.14% | 0.0350 |
| norcia | Percentile | 1.32% | 1.37% | 0.0345 |
| norcia | Otsu | 1.32% | 72.75% | 0.2850 |
| norcia | CNN joint-percentile (chosen on train) | 1.32% | 0.00% | 0.0000 |
| norcia | CNN reflectance (other) | 1.32% | 0.00% | 0.0000 |
| rio | Hardcoded | 5.69% | 2.51% | 0.1755 |
| rio | Percentile | 5.69% | 1.68% | 0.1482 |
| rio | Otsu | 5.69% | 57.09% | 0.4223 |
| rio | CNN joint-percentile (chosen on train) | 5.69% | 0.00% | 0.0000 |
| rio | CNN reflectance (other) | 5.69% | 0.00% | 0.0000 |
| saclay_w | Hardcoded | 1.14% | 9.88% | 0.0045 |
| saclay_w | Percentile | 1.14% | 1.56% | 0.0005 |
| saclay_w | Otsu | 1.14% | 48.90% | 0.5116 |
| saclay_w | CNN joint-percentile (chosen on train) | 1.14% | 0.00% | 0.0000 |
| saclay_w | CNN reflectance (other) | 1.14% | 0.00% | 0.0000 |
| valencia | Hardcoded | 0.44% | 1.69% | 0.0133 |
| valencia | Percentile | 0.44% | 1.40% | 0.0134 |
| valencia | Otsu | 0.44% | 78.25% | 0.2205 |
| valencia | CNN joint-percentile (chosen on train) | 0.44% | 0.02% | 0.0000 |
| valencia | CNN reflectance (other) | 0.44% | 0.00% | 0.0000 |
| dubai | Hardcoded | 9.92% | 0.05% | 0.0032 |
| dubai | Percentile | 9.92% | 1.72% | 0.0500 |
| dubai | Otsu | 9.92% | 79.13% | 0.2323 |
| dubai | CNN joint-percentile (chosen on train) | 9.92% | 0.00% | 0.0000 |
| dubai | CNN reflectance (other) | 9.92% | 0.00% | 0.0000 |
| lasvegas | Hardcoded | 7.67% | 0.27% | 0.0533 |
| lasvegas | Percentile | 7.67% | 1.74% | 0.1548 |
| lasvegas | Otsu | 7.67% | 80.71% | 0.2334 |
| lasvegas | CNN joint-percentile (chosen on train) | 7.67% | 0.02% | 0.0024 |
| lasvegas | CNN reflectance (other) | 7.67% | 0.00% | 0.0000 |
| milano | Hardcoded | 0.80% | 0.42% | 0.1133 |
| milano | Percentile | 0.80% | 1.72% | 0.1219 |
| milano | Otsu | 0.80% | 67.84% | 0.3252 |
| milano | CNN joint-percentile (chosen on train) | 0.80% | 0.00% | 0.0000 |
| milano | CNN reflectance (other) | 0.80% | 0.00% | 0.0000 |
| chongqing | Hardcoded | 7.21% | 1.91% | 0.3102 |
| chongqing | Percentile | 7.21% | 1.74% | 0.2481 |
| chongqing | Otsu | 7.21% | 53.58% | 0.4831 |
| chongqing | CNN joint-percentile (chosen on train) | 7.21% | 0.00% | 0.0000 |
| chongqing | CNN reflectance (other) | 7.21% | 0.00% | 0.0000 |

## v2 pooled test results

| Method | True change | Predicted change | Reported score |
|---|---:|---:|---:|
| Hardcoded | 5.17% | 2.24% | F1 0.0782 |
| Percentile | 5.17% | 1.66% | F1 0.1176 |
| Otsu | 5.17% | 67.35% | OA 0.3439 |
| CNN joint-percentile (chosen on train) | 5.17% | 0.01% | F1 0.0007 |
| CNN reflectance (other) | 5.17% | 0.00% | F1 0.0000 |

## Disclosure and limitations

An earlier preliminary run with a smaller threshold grid also scored the official test split; its pooled F1 values were percentile `0.167`, hardcoded `0.104`, Otsu `0.095`, and CNN `0.0`. This prior test-split use is disclosed because it is not an independent second test. The v2 table above is the main reported result; the earlier values are preliminary, not a competing final estimate.

Results vary widely by city. For example, v2 percentile F1 ranges from `0.0005` (saclay_w) to `0.2481` (chongqing). The tuned hardcoded and percentile settings under-predict change pooled (`2.24%` and `1.66%` predicted against `5.17%` true). Otsu instead predicts `67.35%` of pixels as changed pooled; its pooled OA is `0.3439`, and the per-city table therefore reports OA rather than recall for Otsu.

OSCD does not provide Sentinel-2 SCL in this benchmark layout, so cloud/SCL exclusion is not evaluated. The CNN has near-empty predictions on this test set. A domain gap between the CNN's LEVIR-CD training imagery and OSCD's Sentinel-2 imagery/resolution is a plausible hypothesis for its poor transfer, not a causal conclusion established by these results. City-level variation and the small number of test cities also limit broad generalization.

**TODO:** Add published OSCD baseline results from their original sources, with citations and comparable split/metric protocols. No baseline values are estimated or invented here.

## LaTeX tables

The following tables encode the same v2 per-city and pooled values as above. Include `longtable` and `booktabs` in the paper preamble for the per-city table.

```latex
\begin{longtable}{llrrr}
\caption{OSCD v2 per-city results. Fractions are percentages; score is F1 except Otsu, for which it is OA.}\\
\toprule
City & Method & True change & Predicted change & Score (F1; Otsu OA) \\
\midrule
\endfirsthead
\toprule
City & Method & True change & Predicted change & Score (F1; Otsu OA) \\
\midrule
\endhead
brasilia & Hardcoded & 2.58\% & 0.32\% & 0.0590 \\
brasilia & Percentile & 2.58\% & 1.66\% & 0.1082 \\
brasilia & Otsu & 2.58\% & 69.31\% & 0.3272 \\
brasilia & CNN joint-percentile (chosen on train) & 2.58\% & 0.00\% & 0.0000 \\
brasilia & CNN reflectance (other) & 2.58\% & 0.00\% & 0.0000 \\
montpellier & Hardcoded & 6.79\% & 1.10\% & 0.0355 \\
montpellier & Percentile & 6.79\% & 1.67\% & 0.0490 \\
montpellier & Otsu & 6.79\% & 57.13\% & 0.4514 \\
montpellier & CNN joint-percentile (chosen on train) & 6.79\% & 0.00\% & 0.0000 \\
montpellier & CNN reflectance (other) & 6.79\% & 0.00\% & 0.0000 \\
norcia & Hardcoded & 1.32\% & 5.14\% & 0.0350 \\
norcia & Percentile & 1.32\% & 1.37\% & 0.0345 \\
norcia & Otsu & 1.32\% & 72.75\% & 0.2850 \\
norcia & CNN joint-percentile (chosen on train) & 1.32\% & 0.00\% & 0.0000 \\
norcia & CNN reflectance (other) & 1.32\% & 0.00\% & 0.0000 \\
rio & Hardcoded & 5.69\% & 2.51\% & 0.1755 \\
rio & Percentile & 5.69\% & 1.68\% & 0.1482 \\
rio & Otsu & 5.69\% & 57.09\% & 0.4223 \\
rio & CNN joint-percentile (chosen on train) & 5.69\% & 0.00\% & 0.0000 \\
rio & CNN reflectance (other) & 5.69\% & 0.00\% & 0.0000 \\
saclay\_w & Hardcoded & 1.14\% & 9.88\% & 0.0045 \\
saclay\_w & Percentile & 1.14\% & 1.56\% & 0.0005 \\
saclay\_w & Otsu & 1.14\% & 48.90\% & 0.5116 \\
saclay\_w & CNN joint-percentile (chosen on train) & 1.14\% & 0.00\% & 0.0000 \\
saclay\_w & CNN reflectance (other) & 1.14\% & 0.00\% & 0.0000 \\
valencia & Hardcoded & 0.44\% & 1.69\% & 0.0133 \\
valencia & Percentile & 0.44\% & 1.40\% & 0.0134 \\
valencia & Otsu & 0.44\% & 78.25\% & 0.2205 \\
valencia & CNN joint-percentile (chosen on train) & 0.44\% & 0.02\% & 0.0000 \\
valencia & CNN reflectance (other) & 0.44\% & 0.00\% & 0.0000 \\
dubai & Hardcoded & 9.92\% & 0.05\% & 0.0032 \\
dubai & Percentile & 9.92\% & 1.72\% & 0.0500 \\
dubai & Otsu & 9.92\% & 79.13\% & 0.2323 \\
dubai & CNN joint-percentile (chosen on train) & 9.92\% & 0.00\% & 0.0000 \\
dubai & CNN reflectance (other) & 9.92\% & 0.00\% & 0.0000 \\
lasvegas & Hardcoded & 7.67\% & 0.27\% & 0.0533 \\
lasvegas & Percentile & 7.67\% & 1.74\% & 0.1548 \\
lasvegas & Otsu & 7.67\% & 80.71\% & 0.2334 \\
lasvegas & CNN joint-percentile (chosen on train) & 7.67\% & 0.02\% & 0.0024 \\
lasvegas & CNN reflectance (other) & 7.67\% & 0.00\% & 0.0000 \\
milano & Hardcoded & 0.80\% & 0.42\% & 0.1133 \\
milano & Percentile & 0.80\% & 1.72\% & 0.1219 \\
milano & Otsu & 0.80\% & 67.84\% & 0.3252 \\
milano & CNN joint-percentile (chosen on train) & 0.80\% & 0.00\% & 0.0000 \\
milano & CNN reflectance (other) & 0.80\% & 0.00\% & 0.0000 \\
chongqing & Hardcoded & 7.21\% & 1.91\% & 0.3102 \\
chongqing & Percentile & 7.21\% & 1.74\% & 0.2481 \\
chongqing & Otsu & 7.21\% & 53.58\% & 0.4831 \\
chongqing & CNN joint-percentile (chosen on train) & 7.21\% & 0.00\% & 0.0000 \\
chongqing & CNN reflectance (other) & 7.21\% & 0.00\% & 0.0000 \\
\bottomrule
\end{longtable}

\begin{table}[ht]
\centering
\caption{OSCD v2 pooled test results. Otsu's reported score is OA, not recall.}
\begin{tabular}{lrrl}
\toprule
Method & True change & Predicted change & Score \\
\midrule
Hardcoded & 5.17\% & 2.24\% & F1 0.0782 \\
Percentile & 5.17\% & 1.66\% & F1 0.1176 \\
Otsu & 5.17\% & 67.35\% & OA 0.3439 \\
CNN joint-percentile (chosen on train) & 5.17\% & 0.01\% & F1 0.0007 \\
CNN reflectance (other) & 5.17\% & 0.00\% & F1 0.0000 \\
\bottomrule
\end{tabular}
\end{table}
```
