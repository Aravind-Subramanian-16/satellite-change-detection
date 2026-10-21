# Threats to validity

This document accompanies the current `paper.tex` and `CLAIMS_AUDIT.md`. It
states where the reported evidence can fail, which failures are measurable, and
which are not. It adds no results.

Sources of record: `degradation_results.csv` (SHA-256 `4c301920...`),
`benchmarks/results/oscd_results_v2.json` (SHA-256 `37ffe2bb...`),
`benchmarks/results/oscd_evidence.json` (derived from the v2 JSON),
`benchmarks/results/oscd_loco_thresholds.json` (SHA-256 `32d1dbf5...`,
training cities only), `benchmarks/results/colab_model_check.json` (SHA-256
`ec452724...`) and the code/logs named in the claims audit. OSCD imagery,
LEVIR-CD imagery and the model checkpoint are absent from this checkout.

## 1. Claim boundary

The paper claims:

- a controlled blur-and-resampling study of one frozen CNN on 2,048 LEVIR-CD
  test pairs at six simulated resolutions;
- pooled scores and a descriptive per-image characterisation at 10 m;
- a zero-shot evaluation of the same checkpoint on the ten official OSCD test
  cities, with city-bootstrap intervals;
- pooled scores for train-selected NDVI/NDBI rules and Otsu, reported as
  reference points;
- a training-only leave-one-city-out robustness check of the hardcoded and
  percentile rules, explicitly not a test-set score;
- an explicit disclosure that the OSCD test cities had been scored before the
  reported run.

It does **not** claim a new detector, a competitive OSCD score, operational
accuracy, a validated spectral replacement, a causal role for resolution in the
OSCD result, or validation of the deployed application.

## 2. Construct validity

*Does the experiment measure what the paper says it measures?*

| Threat | Evidence | Direction / severity | Mitigation in the paper | Residual risk |
|---|---|---|---|---|
| **The degradation experiment is synthetic.** It applies blur and resampling to LEVIR-CD RGB, not real Sentinel-2 acquisitions. | `evaluate_degradation.py` applies only `GaussianBlur`, LANCZOS downsampling and LANCZOS upsampling. | The experiment measures sensitivity to one simulated factor, not sensor transfer. High if read as a Sentinel-2 simulation. | Sec. IV-A and Sec. VII list the omitted spectral, radiometric, atmospheric, mixed-pixel and noise factors. | A reader may still equate “10 m simulation” with Sentinel-2 10 m data. Keep the word “simulated” next to every degradation number. |
| **The real-data evaluation confounds resolution with everything else.** OSCD differs in sensor, bands, geography, season, atmosphere and preprocessing. | Separate OSCD data path; no factor isolation on real data. | High for any causal statement about resolution. | The paper says the OSCD result does not identify which factor causes the failure. | The two experiments can be rhetorically merged; do not write “resolution causes the OSCD collapse.” |
| **Binary urban labels are not operational usefulness.** | Metrics are pixel TP/FP/FN against OSCD urban-change masks. | F1 measures overlap, not whether an operator would act. Moderate–high. | Paper calls the output decision support and does not claim field validation. | No user study or cost model; F1 0.1176 does not translate to a workflow benefit. |
| **No SCL / cloud masking in the benchmark.** | The benchmark layout lacks the Scene Classification Layer; cloud masking is off. | Scores may include cloudy or shadowed pixels; live behaviour differs. Moderate. | Stated in Sec. V-A and Sec. VII. | Cloud-mask quality, false masking and cloud-edge artefacts are unquantified. |
| **Coarse-level precision is a near-empty predictor artefact.** At 10 m the model predicts 0.068% of pixels changed. | `degradation_results.csv`; 91,006 predicted pixels out of 134,217,728. | High if precision is read without the predicted fraction. | Sec. IV-B reports predicted fraction, TP/FP counts and true prevalence next to precision. | A reader can still quote 99.47% and ignore the near-empty mask. |
| **Otsu’s headline is overall accuracy, not F1.** Otsu predicts 67.35% of pixels changed. | v2 JSON; OA 0.3439; F1 0.0953. | OA is dominated by the unchanged class and is not comparable with F1. High if mixed. | The table has a separate OA column and the caption explains the choice. | The number can still be quoted out of context. |
| **The spectral rules are deliberately simple.** | Hardcoded NDVI/NDBI and a percentile threshold; no learned spectral model. | The benchmark tests simple reference rules, not the best available spectral method. Moderate. | Paper calls them transparent but weak and does not claim a validated alternative. | The score may understate a tuned spectral method; it is not a literature baseline. |

## 3. Internal validity

*Could the measured result be caused by the protocol rather than the method?*

### 3.1 Degradation implementation

The exact operations are Gaussian blur with radius `factor/2`, LANCZOS
downsampling to `(256/f)×(256/f)`, and LANCZOS upsampling back to 256×256.
At 10 m the intermediate is 12×12. The paper reports no ablation of blur alone
versus resampling alone, no comparison with other interpolation kernels, and no
pixel-grid alignment study. A different interpolation could shift the exact
transition point.

Severity: moderate for the precise 1→2 m boundary; low for the direction of the
collapse, which is visible in recall and predicted fraction. The paper does not
claim that 2 m is a universal threshold.

### 3.2 One checkpoint and one training run

Only one MobileNetV2-based Siamese U-Net checkpoint was evaluated. The training
log records one run (27 epochs, best validation IoU 0.7205), and the saved
evidence contains no seed variation, retraining or architecture comparison. The
checkpoint itself is absent, so its identity and training split cannot be
checked here.

Severity: **high for generalisation beyond this checkpoint**. The paper's claims
are limited to this checkpoint and say so.

### 3.3 Threshold and preprocessing selection

The spectral thresholds and CNN preprocessing were selected on the 14 training
cities. The hardcoded values (NDVI −0.30, NDBI +0.30) sit at the edges of the
search grid; the leave-one-city-out check selected a grid-edge configuration in
all 14 training folds, while percentile 99.0 was interior in all 14. The full
selection log and the CNN’s training scores are not retained. No test labels
were used to fit the v2 thresholds according to the project record, but this is
documented rather than independently audited.

Severity: moderate for interpreting the hardcoded score as an optimum. A wider
grid could improve or degrade it; the direction is unknown.

### 3.4 Repeated use of the test split

The ten official test cities had been scored before the reported v2 run. An
earlier preliminary run with a smaller grid produced pooled F1 values of 0.167
(percentile), 0.104 (hardcoded), 0.095 (Otsu) and 0.0 (CNN). The total number of
scoring events is not recorded. The v2 run re-evaluated the same cities after
the configuration was fixed on training cities.

Severity: **high for any claim of unbiased generalisation**, low for the
descriptive claim “these are the measured v2 scores.” The paper makes only the
latter. The difference between the preliminary percentile value (0.167) and v2
(0.1176) is itself a warning that test-set decisions matter.

### 3.5 Metric arithmetic

Pooled values come from summed TP/FP/FN, not from averaging per-image F1. The
saved v2 JSON was independently recomputed from confusion counts, and the
evidence file matches to four decimals. Remaining risks:

- **Per-image precision convention.** `evaluate_degradation.py` sets per-image
  precision to 1.0 when an image has no predicted positives. The paper reports
  pooled precision from summed counts, not a macro-average, so this convention
  does not enter the reported values. A reader who computes a macro-average will
  get different numbers.
- **Zero denominators.** CNN reflectance has zero predicted positives, so
  precision is reported as 0 by convention.
- **Pooling weights pixels, not cities.** Large cities dominate the pooled
  scores. Per-city values are shown separately, but no city-macro score is
  reported.
- **Rounding.** Displayed values are rounded; small differences should not be
  over-interpreted, especially for near-empty CNN predictions.

Severity: low for the reported values; moderate for cross-paper comparison if
another paper defines zero-denominator metrics differently.

### 3.6 The 10 m per-image bins are descriptive

The 924/4/5/2 split was computed after seeing the saved results. It was not a
pre-specified endpoint. It is useful for showing that failure is dominated by
empty predictions rather than false positives, but it is not a hypothesis test.

Severity: low as description; moderate if treated as a mechanistic finding.

## 4. External validity

*Do the results generalise beyond these scenes, cities and sensor?*

| Threat | Evidence | Direction / severity | Mitigation | Residual risk |
|---|---|---|---|---|
| **Ten OSCD cities only.** | 10 test cities; percentile F1 0.0005–0.2481; hardcoded 0.0032–0.3102. | Pooled scores hide large heterogeneity; city ranking is unstable. High for population claims. | Per-city figure and ranges; pooled intervals resample cities. | No basis for a global accuracy estimate. |
| **One sensor family.** | LEVIR-CD aerial RGB and Sentinel-2 optical bands. | Results may not transfer to SAR, hyperspectral, 30 m or sub-metre data. High for cross-sensor claims. | Scope stated; no cross-sensor claim. | A user may apply the urban score elsewhere. |
| **LEVIR-CD scene content.** | Aerial imagery with a particular geography, season and label definition. | The degradation curves may differ on other scenes. Moderate. | Scene content is held fixed within the experiment, which is both a strength and a scope limit. | No second aerial dataset. |
| **OSCD acquisition era and processing baseline.** | Released OSCD pairs. | Atmospheric correction, calibration and urban patterns may differ from current data. Moderate. | No temporal generalisation claim. | Live-tool behaviour on new scenes may differ. |
| **Urban-change label definition.** | Binary OSCD urban masks. | A “change” in another application may not match the label. High for cross-domain use. | Claims restricted to OSCD urban change. | No ontology mapping or cross-dataset test. |
| **The live application is not validated.** | Benchmark path differs from upload/live paths; scene selection, SCL masking and UI are not exercised. | Any implied end-to-end accuracy is unsupported. High. | System overview is explicitly implementation facts, not validation. | A demo can still be mistaken for a validated service. |

## 5. Statistical conclusion validity

- **The pooled intervals resample ten cities.** They reflect city sampling only;
  the cities are not a random sample. A different ten cities could move the
  pooled values materially.
- **The paired percentile-minus-hardcoded interval includes zero**
  (−0.0176 to +0.0778). The paper does not rank the two rules. A point estimate
  of +0.0394 is not evidence of a reliable difference.
- **Per-city intervals ignore spatial correlation.** They resample pixels
  independently; neighbouring pixels are correlated, so these intervals are
  approximations, not coverage guarantees.
- **No interval is reported for overall accuracy.** The OA values are point
  estimates.
- **No training or selection uncertainty is included.** One checkpoint, one
  training run and a threshold-selection procedure without a retained
  uncertainty distribution.
- **Near-zero CNN counts are fragile.** Joint-percentile has 54 TP and 127 FP;
  small count changes can move F1 by more than the reported third decimal.
- **Multiple descriptive metrics.** The paper reports F1, IoU, precision,
  recall, OA and predicted fraction. No multiplicity correction is applied
  because no confirmatory hypothesis test is claimed.
- **The 0.5 decision threshold is untuned.** No threshold sweep is reported, so
  the CNN scores are conditional on that fixed threshold.

Severity: moderate–high for interval-based ranking claims; low for the
descriptive statement that the CNN predictions are near empty and the spectral
rules under-predict change.

## 6. Reproducibility validity

- The v2 JSON and degradation CSV are tracked with recorded SHA-256 values. The
  figure generator reads only those files and will fail on missing methods,
  duplicate rows, non-test rows or incomplete coverage.
- OSCD imagery, LEVIR-CD imagery and the checkpoint are **not** in the
  checkout. Neither benchmark can be re-executed here; only the arithmetic and
  figures can be reproduced.
- The v2 benchmark code commit is recorded as Phase E `a6dad9e`; later changes
  are documentation, figures and tests. Recheck this if benchmark code changes.
- No container digest or lockfile exists for the original run. Dependency
  ranges may resolve differently in the future.
- LaTeX could not be compiled here (`pdflatex`, `tectonic` and `latexmk` are
  absent). The manuscript is structurally checked but not PDF-verified.
- The Colab notebooks for the learned classifier and validation search were not
  run locally and have no pasted outputs. They are unverified, not evidence. The
  separate `run_all_colab` hand-off did run on 2026-10-21 at `e8b6678`; its LOCO
  and model-check outputs are training-only checks and add no test score.

See `ARTIFACT.md` for commands, hashes and owner actions.

## 7. Ethical, legal and dual-use validity

- **Automation bias.** A heatmap can be read as ground truth. The UI and paper
  say decision support and human verification are required, but no user study
  measures whether the warning works.
- **Dual use.** The tool is intended for civil land observation, not targeting
  or enforcement, but change detection is dual-use. The paper states intended
  use; it cannot control downstream use.
- **Privacy.** The app can store previews and AOI locations in a local SQLite
  history and has no authentication. Public deployment would create privacy and
  access-control risks. This is a deployment limitation, not a benchmark
  finding.
- **Licensing.** OSCD terms are recorded in project notes as CC BY-NC-SA but
  have not been verified externally; commercial use may be restricted. OSM
  context is ODbL; Copernicus data has its own terms. The repository does not
  redistribute OSCD imagery or labels. Legal review is required before
  redistribution or commercial use. No code licence has been chosen.
- **AI-assistance disclosure.** The manuscript and code were prepared with AI
  assistance; the chosen venue's policy must be checked and followed.

## 8. Threat summary

| Validity type | Main threat | Severity | Can existing evidence fix it? |
|---|---|---|---|
| Construct | Synthetic degradation is not Sentinel-2 | High if misread | No; needs real multi-resolution data |
| Construct | OSCD confounds resolution with sensor/atmosphere/geography | High for causal claims | No; needs factor isolation |
| Construct | No SCL/cloud masking | Moderate | No; needs an SCL-preserving benchmark |
| Internal | Test split scored before v2; total events unrecorded | High for generalisation | No; needs an untouched city set |
| Internal | One checkpoint and one training run; checkpoint absent | High for generalisation and reproduction | Owner must supply artefacts; new runs needed for scope |
| Internal | Grid-edge thresholds; incomplete selection log | Moderate | Wider pre-registered grid needed |
| Internal | 10 m bins chosen after seeing results | Low as description | Keep descriptive; do not test hypotheses post hoc |
| External | Ten cities, one sensor family, one label source | High | New multi-region/multi-sensor labels needed |
| Statistical | n=10 city bootstrap; no OA interval; paired CI includes zero | Moderate–high | Better design needed; not fixable by more arithmetic |
| Reproducibility | Imagery/weights absent; PDF uncompiled; learned/auto Colab unrun; local model inference unverified | High | Owner actions listed in `ARTIFACT.md` |
| Ethics/legal | Automation bias, dual use, privacy, licence ambiguity | High for deployment | Human review, authentication, legal review |

## 9. What would change the conclusions

- A second architecture or checkpoint that survives 2 m or 10 m blur/resampling;
  that would weaken generalisation from this checkpoint but not erase the
  measured curve.
- Real acquisitions of the same scenes at multiple resolutions, which would
  separate resolution from sensor differences.
- A genuinely untouched city set or a new dataset, which would provide an
  independent OSCD-style estimate.
- An SCL-preserving benchmark showing cloud masking materially changes the
  spectral scores.
- A wider threshold grid or a tuned decision threshold showing the hardcoded
  and CNN results are substantially different from the reported ones.
- A blur-only versus resampling-only ablation locating the transition more
  precisely.
- A user study showing whether operators verify candidates or defer to the
  heatmap.

Until at least one of these exists, the paper's descriptive and negative
framing is the strongest defensible claim.

## 10. Bottom line

The reported numbers are internally consistent and honestly limited: they are
descriptive scores from one frozen checkpoint, saved test-set files, a
training-only LOCO check, a synthetic degradation protocol and a small test
split that had been used before. They do not establish operational accuracy,
general change-detection ability, a validated spectral fallback or a causal role
for resolution in the OSCD result. Every use of these numbers should carry the
city count, the single label source, the one-checkpoint scope and the prior
scoring history.
