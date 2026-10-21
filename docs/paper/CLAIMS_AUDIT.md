# Claims audit

Audit date: 2026-10-21. Scope: every quantitative or comparative claim in the
current `docs/paper/paper.tex`, plus claims a reader could infer from the
abstract, tables and figures. This audit replaces the Phase F version, which
described an earlier manuscript.

Sources of record:

| Source | Role | SHA-256 |
|---|---|---|
| `degradation_results.csv` | per-image TP/FP/FN at six factors (2,048 images) | `4c301920d03d09dbc416d82fa76b93e76e1fab9b74bc2db5155da9735965fa88` |
| `benchmarks/results/oscd_results_v2.json` | saved per-city v2 test confusion counts (50 rows) | `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f` |
| `benchmarks/results/oscd_evidence.json` | baselines, bootstrap intervals and paired differences computed from the v2 JSON | generated, not an independent score |
| `benchmarks/results/oscd_loco_thresholds.json` | train-only leave-one-city-out robustness (14 training cities, no test label) | `32d1dbf57d83a1c68c76de0d64856795c082498788428c8206fd7cf2a4a2e29d` |
| `benchmarks/results/colab_model_check.json` | Drive `model.onnx` size, SHA-256, onnxruntime load and input names | `ec452724a09c915a6577b535146bd78fe5f09dd9ce13421d8359057709c3902a` |
| `benchmarks/results/COLAB_RUN_SUMMARY.md` | rendered summary of the two saved files and the Colab pytest line | `77177c595f2a80aa71c3e9d5ff2dc9b31bf7b976a5a909e1a58152507dffeca6` |
| `evaluate_degradation.py` | degradation and inference implementation | tracked code |
| `training_log.txt`, `train.py`, `README.md` | training-run record and configuration | tracked files |
| `PAPER_NOTES.md` | v2 selection and scoring-history notes | tracked file |

The LEVIR-CD imagery, OSCD imagery/labels and the model checkpoint are **absent
from this checkout**. Code and saved logs can be inspected, but neither
benchmark can be re-executed here.

Status meanings:

- **Supported** — reproduced from a tracked file in this checkout.
- **Partially supported** — the files support the wording, but a stronger
  interpretation, an external fact, or a missing artefact prevents full
  verification.
- **Unverified** — requires data, weights or an external check that is absent.
- **Not claimed** — explicitly excluded; must not appear as a result.

## Degradation experiment

| ID | Claim (paper location) | Evidence | Status | Action |
|---|---|---|---|---|
| D1 | One MobileNetV2-based Siamese U-Net with a 3D fusion module was trained once on LEVIR-CD and frozen (Sec. IV-A) | `model.py` defines the architecture; `training_log.txt` records one run; `evaluate_degradation.py` only loads the state dict and calls `eval()` | Partially supported | The checkpoint is absent, so its identity and training provenance cannot be checked here. Keep "one architecture, one training run"; do not generalise. |
| D2 | Training used Dice + BCE, AdamW (lr 5e-4, weight decay 1e-4), batch 4, cosine annealing, up to 100 epochs, patience 10; stopped after 27 epochs; best validation IoU 0.7205 (Sec. IV-A) | `train.py` configuration; `training_log.txt` (“Early stopping triggered after 27 epochs”, “Best Validation IoU: 0.7205”); `README.md` | Supported as logged | These are log values, not an independent rerun. Do not quote the validation IoU as a test score. |
| D3 | The evaluation uses 2,048 LEVIR-CD test pairs (Sec. IV-A) | `degradation_results.csv`: 12,288 rows = 2,048 unique images × 6 factors | Supported | Keep. |
| D4 | For factor f > 1: Gaussian blur radius f/2, LANCZOS downsample to (256/f)×(256/f), LANCZOS upsample to 256×256; at 10 m the intermediate is 12×12 (Sec. IV-A) | `evaluate_degradation.py:degrade_image`, factors `[1, 2, 4, 8, 16, 20]` and resolution map | Supported | Keep the exact wording; do not call this a sensor simulation. |
| D5 | Inputs were ImageNet-normalised and thresholded at 0.5 (Sec. IV-A) | `evaluate_degradation.py:preprocess_numpy`; `preds = (probs > 0.5)` | Supported | Keep. |
| D6 | Pooled precision/recall/F1/IoU at 0.5, 1, 2, 4, 8 and 10 m are the six rows of Table I (Sec. IV-B) | Recomputed from summed TP/FP/FN in `degradation_results.csv`; matches `generated_degradation_table.tex` | Supported | Keep; the caption states pooled counts, not per-image averages. |
| D7 | F1 is 87.06% at 0.5 m, 70.81% at 1 m (a 16.25-point drop), 4.41% at 2 m, 2.84% at 4 m and 2.61% at 8–10 m (Sec. IV-B, Abstract, Conclusion) | Recomputation from the CSV | Supported | Keep. The 16.25-point figure is 87.06 − 70.81, rounded from unrounded values. |
| D8 | Precision is 88.82, 93.43, 90.78, 97.69, 99.59 and 99.47%; recall is 85.36, 57.01, 2.26, 1.44, 1.32 and 1.32% (Sec. IV-B) | Recomputation from the CSV | Supported | Keep; the paper says the F1 decline is recall-dominated. |
| D9 | At 10 m, 91,006 of 134,217,728 pixels are predicted changed (0.068%); 6,837,404 ground-truth pixels are changed; precision uses 90,527 TP and 479 FP (Sec. IV-B) | Recomputation from factor-20 rows; 134,217,728 = 2,048 × 256 × 256 | Supported | Keep. 479 FP is a count, not a rate; do not describe it as a false-positive rate. |
| D10 | Of 935 changed test images at 10 m, 924 (98.82%) have no predicted change; the remaining 11 split into 4 with IoU < 0.1, 5 in [0.1, 0.5) and 2 at or above 0.5 (Sec. IV-C) | Recomputation from factor-20 rows; per-image IoU values listed in `DRAFT_CORRECTION_LOG.md` | Supported | Keep. These are counts from one run, not a sampling estimate. |
| D11 | The high coarse-level precision describes how little the model predicts, not how well it localises change (Sec. IV-B) | Predicted fraction 0.068% versus 5.09% true changed pixels (6,837,404 / 134,217,728) | Supported as interpretation | Keep the predicted fraction next to precision. Do not call the coarse result useful detection. |
| D12 | The degradation procedure holds scene content fixed and varies blur/sampling; it does not reproduce Sentinel-2 spectral, radiometric, atmospheric, mixed-pixel or noise differences (Sec. IV-A, VII) | Implementation applies only blur/resampling to LEVIR-CD RGB; the OSCD path is separate | Supported as a design statement | Keep both clauses; never present the simulation as real Sentinel-2 data. |
| D13 | The prediction-behaviour counts are descriptive and do not separate resolution loss from other differences (Sec. IV-C) | No ablation of blur versus resampling was run | Supported as a limitation | Keep the non-causal wording. |

## OSCD evaluation

| ID | Claim (paper location) | Evidence | Status | Action |
|---|---|---|---|---|
| O1 | OSCD provides 14 training cities and 10 official test cities with pixel-level urban-change labels (Sec. V-A) | `benchmarks/oscd_eval.py` split handling; `PAPER_NOTES.md`; v2 JSON has 10 test cities | Supported by project records | The dataset is absent; cite the official dataset paper and split after verification. |
| O2 | Five bands (B02, B03, B04, B08, B11) are used; the pooled test set has 3,077,936 pixels, 5.17% labelled change (Sec. V-A) | v2 JSON confusion counts; `oscd_evidence.json` | Supported | Keep; 3,077,936 is the sum of TP+FP+FN+TN for every configuration. |
| O3 | The benchmark layout has no SCL, so cloud/shadow exclusion is not evaluated (Sec. V-A, VII) | `benchmarks/oscd_eval.py` runs with cloud masking off; `PAPER_NOTES.md` | Supported | Keep; do not imply the scores include cloud masking. |
| O4 | Hardcoded rule: NDVI drop ≥ 0.30 or NDBI rise ≥ 0.30; percentile rule: 99.0th percentile; Otsu thresholds the same evidence; settings selected on the 14 training cities over fixed grids; no test labels used to fit v2 thresholds (Sec. V-A) | `PAPER_NOTES.md`; `benchmarks/oscd_eval.py` selection path | Partially supported | The code path and notes support the wording, but the full selection log is not retained and the total scoring history is not recorded. Do not claim a fully audited train/test separation. |
| O5 | The selected hardcoded values sit at grid edges; 99.0 is interior to the percentile grid (Sec. V-A, Discussion, Limitations) | `PAPER_NOTES.md`; grid definitions in `benchmarks/oscd_eval.py` | Supported | Keep; a wider grid was not tested. |
| O6 | The CNN input is an RGB stack (B04, B03, B02); reflectance scaling is raw/10,000 to 0–255; joint-percentile scaling uses the 2nd/98th percentiles of both dates combined; 256×256 tiles with 32-pixel overlap and averaged probabilities; joint-percentile selected on training cities (Sec. V-A) | `benchmarks/oscd_eval.py`; `PAPER_NOTES.md` | Partially supported | Code supports the mechanics; the CNN selection scores are not retained. Reflectance is described as the alternative, not a second tuned model. |
| O7 | The ten test cities had been scored before the reported v2 run; an earlier preliminary run with a smaller grid produced pooled F1 0.167 (percentile), 0.104 (hardcoded), 0.095 (Otsu) and 0.0 (CNN); the total number of scoring events is not recorded; v2 is not an independent test (Sec. V-A, Abstract, Limitations) | `PAPER_NOTES.md` disclosure paragraph; `DRAFT_CORRECTION_LOG.md` | Supported by project record | Keep the disclosure in the abstract and results. Never describe v2 as a fresh or independent test. |
| O8 | Percentile rule: pooled precision 0.2419, recall 0.0777, F1 0.1176, 95% city-bootstrap CI 0.0540–0.1802; predicts 1.66% (Sec. V-B, Table II) | Recomputed from v2 JSON; `oscd_evidence.json`; matches `generated_oscd_table.tex` | Supported | Keep; intervals resample the ten cities, not pixels or runs. |
| O9 | Hardcoded rule: pooled F1 0.0782, CI 0.0168–0.1846; predicts 2.24% against 5.17% true change (Sec. V-B) | v2 JSON; `oscd_evidence.json` | Supported | Keep. |
| O10 | Paired percentile-minus-hardcoded F1 difference is +0.0394, bootstrap interval −0.0176 to +0.0778, which includes zero; the ranking is not resolved at the 5% level (Sec. V-B) | `oscd_evidence.json` paired bootstrap (seed 0, 10,000 resamples) | Supported | Keep. Do not say percentile is significantly better. |
| O11 | A random predictor at 5.17% prevalence has F1 0.0517; only the percentile interval lies entirely above it, narrowly (Sec. V-B) | `oscd_evidence.json` baselines; percentile lower bound 0.0540 | Supported | Keep "narrowly". The hardcoded and Otsu intervals include 0.0517. |
| O12 | Otsu predicts 67.35% of pixels changed, reaches OA 0.3439, precision 0.0513, recall 0.6684 and F1 0.0953 (CI 0.0495–0.1245); OA is its headline score because F1 is not a useful standalone summary at this predicted fraction (Sec. V-B, Abstract) | v2 JSON; `oscd_evidence.json`; `generated_oscd_table.tex` includes OA | Supported | Keep the OA caveat wherever Otsu appears. Do not compare 0.3439 with F1 values as if they were the same metric. |
| O13 | CNN joint-percentile predicts 0.01% of pixels and reaches F1 0.0007 (CI 0.0000–0.0017); reflectance predicts 0.00% and F1 0.0000; both have OA 0.9483, equal to all-no-change (Sec. V-B, Abstract) | v2 JSON; `oscd_evidence.json`; per-city JSON | Supported | Keep. Do not call OA 0.9483 evidence of detection. |
| O14 | Percentile per-city F1 ranges 0.0005 (saclay_w) to 0.2481 (chongqing); hardcoded ranges 0.0032 (dubai) to 0.3102 (chongqing); joint-percentile CNN predicts no change in 8/10 cities and at most 0.0024 (lasvegas); reflectance predicts none (Sec. V-C, Fig. 2) | v2 JSON; `PAPER_NOTES.md` per-city table; `oscd_evidence.json` | Supported | Keep as descriptive ranges. Do not rank cities as generalisable. |
| O15 | Pooled intervals resample the ten cities; per-city intervals resample pixels independently and ignore spatial correlation; neither includes training or threshold-selection uncertainty (Sec. V-C) | `benchmarks/oscd_evidence.py`; `scripts/make_paper_figures.py` | Supported as method description | Keep the disclosure; do not describe the intervals as confidence guarantees. |
| O16 | City-level variation is descriptive; the simulation isolates blur/resampling, while OSCD confounds resolution with spectral, radiometric, atmospheric and geographic differences; cloud effects are uncontrolled (Sec. V-C, Discussion) | Study design; no factor-isolation experiment on OSCD | Supported as a limitation | Never attribute the OSCD CNN failure to resolution alone. |
| O17 | Only one architecture and one training run were tested; there was no retraining, fine-tuning, seed variation or architecture comparison (Sec. VII, Abstract) | One checkpoint; training log; no other runs recorded | Supported as scope | Keep; do not generalise to “CNNs”. |
| O18 | No confidence intervals are reported for overall accuracy (Sec. VII) | `oscd_evidence.json` stores OA without intervals | Supported | Keep; do not add intervals without recomputation. |
| O19 | All test-set scores and per-image counts come from the two saved files named in Sec. VII; the training-only robustness values come from a third file; the figure/table generator reads the two test-set files only and records their hashes | `scripts/make_paper_figures.py`; `figure_manifest.json`; SHA-256 values above | Supported | Keep. Regenerating figures must not read imagery or re-score a city. |
| O20 | The benchmark evaluates the offline pipeline and frozen checkpoint, not the deployed application's scene selection or user interface (Sec. VII) | `benchmarks/oscd_eval.py` versus `app.py`/`live_pipeline.py` | Supported by code structure | Keep; the system overview is implementation description, not end-to-end validation. |
| O21 | The upload path runs a CNN; the live path queries the Copernicus catalogue, ranks scenes, applies SCL masking and computes NDVI/NDBI differences; the interface withholds accuracy for unvalidated profiles (Sec. III) | `app.py`, `live_pipeline.py`, `scene_selection.py`, `static/app.js`, `profiles/validation_status.json`; tests | Supported as implementation facts | Keep the sentence that this section is not an end-to-end validation. |
| O22 | Train-only leave-one-city-out check: pooled held-out F1 0.0976 hardcoded (IoU 0.0513, precision 0.0838, recall 0.1168) and 0.1469 percentile (IoU 0.0793, precision 0.1544, recall 0.1401); hardcoded selection at a search-grid edge in all 14 folds, percentile in none (Sec. V-B, VII) | `benchmarks/results/oscd_loco_thresholds.json`; `benchmarks/results/COLAB_RUN_SUMMARY.md` | Supported as a saved training-only run | This is not a test-set score and adds no test-scoring event. Do not compare it directly with the v2 test F1 as though it were test performance. The hardcoded scores are limited by the search grid. |

## General claims

| ID | Claim (paper location) | Evidence | Status | Action |
|---|---|---|---|---|
| G1 | Related-work statements about LEVIR-CD, Sentinel-2, Siamese networks, STANet, BIT, NDVI, NDBI, Otsu, OSCD, domain shift and test-set reuse | 15 `[CITE: ...]` occurrences (14 body slots plus one explanatory example); no bibliography exists | Unverified | Replace every body slot with a verified source and check the surrounding sentence. Do not submit with placeholders. |
| G2 | The paper makes no priority or originality claim (Abstract, Introduction, Conclusion) | Static check finds no prohibited priority or originality wording | Supported as wording | Keep the hedged framing; complete an external prior-work search before any stronger statement. |
| G3 | Author block: Aravind, Department of Computer Science and Engineering, Presidency University, Bengaluru | Supplied by the owner and present in the revised DOCX | Partially supported | Confirm the spelling, affiliation and whether an email is required before submission. |
| G4 | Drive `model.onnx` is 33,268,410 bytes, SHA-256 `41c2ab64...`, loads in onnxruntime and exposes inputs `input_a`, `input_b` | `benchmarks/results/colab_model_check.json` | Supported as a Colab artifact check | This verifies the file, not app-level inference. The model is still absent from this checkout, so the deployed app path remains unverified. |

## Claims explicitly not made

- No priority or originality claim; no best-method claim; no comparison with
  published OSCD scores.
- No claim that resolution is the sole cause of the OSCD CNN failure. The
  degradation experiment isolates blur/resampling; the real-data evaluation
  confounds several factors.
- No claim that NDVI/NDBI rules are a validated low-resolution alternative.
  They are transparent reference points with low pooled F1 and wide city
  variation.
- No claim that Otsu is a usable detector; it predicts 67.35% of pixels changed
  and its OA is 0.3439.
- No claim that coarse-resolution precision reflects useful localisation.
- No claim of operational, safety-critical, legal or enforcement accuracy.
- No claim that the deployed application, scene selection, cloud masking or
  user interface has been validated end to end.
- No accuracy claim for agriculture, deforestation, roads or any other
  unvalidated profile.
- No claim that ten cities are representative of global urban change.
- No causal claim about domain gap, season, atmosphere or preprocessing.
- No commercial-use or redistribution permission for OSCD, Copernicus or OSM
  data.

## Numerical consistency checks

- Degradation CSV: 12,288 rows, 2,048 unique images, factors 1/2/4/8/16/20.
  Recomputing pooled TP/FP/FN reproduces every Table I value to two decimals.
- At factor 20: 935 changed images, 91,006 predicted pixels, 6,837,404 changed
  ground-truth pixels, 90,527 TP, 479 FP, and 924/4/5/2 images in the reported
  IoU bands.
- OSCD v2 JSON: 50 rows (10 cities × 5 configurations), all `split: "test"`;
  every configuration pools to 3,077,936 pixels.
- `oscd_evidence.json` recomputes pooled metrics from the JSON confusion counts
  and reports city-bootstrap intervals (seed 0, 10,000 resamples); it does not
  read imagery or test labels.
- `oscd_loco_thresholds.json` reports 14 training-city folds, no official test
  city in `train.txt`, no accepted test-label path, and `result_status:
  computed_on_training_cities_only`; the two families pool to F1 0.0976 and
  0.1469, and the hardcoded family records a grid-edge warning in 14/14 folds
  while the percentile family records none.
- `colab_model_check.json` records size 33,268,410 bytes, expected size equal,
  onnxruntime load `true`, inputs `input_a`/`input_b`, and the full SHA-256
  `41c2ab6466408a6d23339a3c424307f6aa7b7f9063fe702d161b6f4685152bf9`.
- The `COLAB_RUN_SUMMARY.md` hash above matches the regenerated summary, and the
  summary's recorded source hashes match the two JSON files.
- `docs/paper/figures/figure_manifest.json` records the v2 JSON hash and the
  degradation CSV hash used for the current figures.
- Static LaTeX check (with `\input` expanded): 77 opening and 77 closing braces,
  all four labels resolve, all four referenced assets exist, 15 citation slots.
