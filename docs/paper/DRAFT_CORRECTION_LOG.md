# Draft correction log

Date: 2026-10-21
Step: 1 (correct the existing draft without altering the original)

## Source and working copy

The draft was **not** present in `docs/paper/` when this step began. It was found at:

```text
/Users/aravind/Downloads/IEEE_Paper_Draft_Resolution_Mismatch_Change_Detection.docx
```

The original was left untouched. Evidence:

| Item | Size | SHA-256 |
|---|---:|---|
| Original (Downloads) | 100,962 bytes | `69442ffb872507d03ae2d8d0c737ec00a3d9fcd1e30ec06a68e677b643c49056` |
| Revised copy in `docs/paper/` | 102,768 bytes | `ffb084fc440e7869c58061a818aa14dbebdce61570f76a1d18e80e848fa315b7` |

Revision note (2026-10-21): the revised copy and this log were corrected after
rechecking the per-image IoU values at 10 m. The first revision grouped
`test_77_768_768.png` (IoU 0.0556) in the 0.1--0.5 band; it belongs in the
IoU < 0.1 band. The corrected bins are 924 + 4 + 5 + 2 = 935. The table,
surrounding text and this log now use those counts. The original DOCX in
Downloads was not opened for writing.

Inputs used for verification:

| File | SHA-256 |
|---|---|
| `degradation_results.csv` | `4c301920d03d09dbc416d82fa76b93e76e1fab9b74bc2db5155da9735965fa88` |
| `benchmarks/results/oscd_results_v2.json` | `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f` |
| `PAPER_NOTES.md` | `e0c0205ece2ce4e2a82529829eab69f952d81bf61ba2dfb7faf7c628487050a9` |
| `training_log.txt` | `27a13e880722a491926c590861dc5c1e5918110a3aedb8494bf5b0f3811e1b60` |

No OSCD data or model checkpoint is present locally. No test city was re-scored and no
model was trained for this correction.

## Corrections

### 1. Title and framing

- Original title: “Resolution-Induced Performance Collapse in CNN-Based Satellite Change
  Detection: A Case for Spectral Index Alternatives.”
- Revised title: “Resolution-Induced Performance Collapse of a CNN Change Detector:
  Simulated and Real Sentinel-2 Evidence.”
- Reason: the original title implies that spectral indices are a proven alternative.
  The saved OSCD results show pooled F1 0.0782–0.1176 for the tested spectral rules,
  which does not support that implication.
- Evidence: `benchmarks/results/oscd_results_v2.json` aggregate rows.

### 2. Abstract

Replaced the abstract so that it:

- states one architecture and one training run;
- reports the verified native and degraded metrics;
- states that blur-and-resampling alone is sufficient, rather than claiming resolution
  is the sole cause of real Sentinel-2 failure;
- adds the zero-shot OSCD results rather than describing them as future work;
- says the OSCD test cities had been scored more than once and makes no one-shot claim;
- says the spectral rules are not a validated alternative.

Evidence: Table I below, plus the v2 JSON aggregates.

### 3. Table I (degradation results)

The six rows were already numerically correct. Values were recomputed from
`degradation_results.csv` by summing `tp`, `fp` and `fn` over all 2,048 images at each
factor, then applying:

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
IoU       = TP / (TP + FP + FN)
```

Recomputed values (percent):

| Factor | Resolution | TP | FP | FN | Precision | Recall | F1 | IoU |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.5 m | 5,836,700 | 734,468 | 1,000,704 | 88.82 | 85.36 | 87.06 | 77.08 |
| 2 | 1.0 m | 3,897,947 | 274,120 | 2,939,457 | 93.43 | 57.01 | 70.81 | 54.81 |
| 4 | 2.0 m | 154,530 | 15,702 | 6,682,874 | 90.78 | 2.26 | 4.41 | 2.25 |
| 8 | 4.0 m | 98,511 | 2,328 | 6,738,893 | 97.69 | 1.44 | 2.84 | 1.44 |
| 16 | 8.0 m | 90,480 | 370 | 6,746,924 | 99.59 | 1.32 | 2.61 | 1.32 |
| 20 | 10.0 m | 90,527 | 479 | 6,746,877 | 99.47 | 1.32 | 2.61 | 1.32 |

All Table I entries in the revised draft match these recomputed values.

### 4. “Stable between 0.5 m and 1 m”

- Original: “Performance is stable between 0.5 m and 1 m but collapses sharply beyond
  that point.”
- Revised: F1 falls from 87.06% to 70.81% between 0.5 m and 1 m, a 16.25-point absolute
  drop, and then to 4.41% at 2 m.
- Evidence: Table I / `degradation_results.csv`.

### 5. “Precision remains above 97% throughout”

This was false. The precision column is 88.82, 93.43, 90.78, 97.69, 99.59 and 99.47.
The revised text gives all six values. It also states that the coarse-level precision is
computed from very few predicted positives:

- at 10 m, predicted pixels = TP + FP = 90,527 + 479 = 91,006;
- total pixels = 2,048 × 256 × 256 = 134,217,728;
- predicted fraction = 91,006 / 134,217,728 = 0.0678% (0.068% rounded);
- changed ground-truth pixels at 10 m = TP + FN = 6,837,404.

The revision therefore does not treat high precision at 2–10 m as evidence of useful
detection.

### 6. Table II sum (934 vs 935)

The original table had categories 924 + 6 + 4 = 934 under a caption of n = 935, and the
text said 98.8% zero predictions. The revised table uses definitions directly
computable from the saved CSV, among the 935 changed images at 10 m:

| Behavior | Count | Percentage of 935 |
|---|---:|---:|
| No predicted change pixels | 924 | 98.82% |
| Predicted, IoU < 0.1 | 4 | 0.43% |
| Predicted, 0.1 ≤ IoU < 0.5 | 5 | 0.53% |
| Predicted, IoU ≥ 0.5 | 2 | 0.21% |
| Total | 935 | 100.00% |

The 11 non-empty predictions are:

- IoU < 0.1: `test_113_768_768.png` (0.0107), `test_77_768_768.png` (0.0556),
  `test_54_512_0.png` (0.0727), `test_102_256_256.png` (0.0964);
- 0.1 ≤ IoU < 0.5: `test_102_0_512.png` (0.1088), `test_104_512_0.png` (0.1130),
  `test_102_256_768.png` (0.1795), `test_89_512_256.png` (0.3841),
  `test_89_512_512.png` (0.4318);
- IoU ≥ 0.5: `test_16_0_256.png` (0.7269), `test_71_768_768.png` (0.6238).

The component percentages sum to 99.99 because of rounding; the table's total
row is 100.00% by definition.

### 7. Degradation method description

The original said “Gaussian blur with kernel size and sigma scaled to the target
degradation factor, downsampling with area-based interpolation, and upsampling back …
using bicubic interpolation.” The code does not do that.

`evaluate_degradation.py:19-31`:

- `sigma = factor / 2.0`;
- `ImageFilter.GaussianBlur(radius=sigma)` — PIL uses a radius, not an explicit kernel
  size/sigma pair;
- downsample to `(w // factor, h // factor)` using `Image.LANCZOS`;
- upsample back to original size using `Image.LANCZOS`.

The revised draft states those operations exactly and notes that 10 m corresponds to a
12×12 intermediate for a 256×256 input. It does not claim area-based or bicubic
resampling.

### 8. Training description

- Original: “trained for 100 epochs with early stopping (patience = 10) … Adam
  optimizer.”
- Revised: configured for up to 100 epochs; stopped after 27 epochs; best validation IoU
  0.7205; AdamW with weight decay `1e-4`; batch size 4; cosine annealing; one training
  run.
- Evidence: `train.py` (optimizer, scheduler, batch size, patience) and
  `training_log.txt` (“Early stopping triggered after 27 epochs”, “Best Validation IoU:
  0.7205”).
- The draft's training/validation split counts (5,120 / 1,024 pairs) could not be
  verified because `dataset/` is absent. They were removed. **SOURCE NOT FOUND —
  unverified.**

### 9. Unverified comparative and qualitative claims removed

Removed or reframed, with reason:

| Original claim | Action | Reason |
|---|---|---|
| Models “routinely report F1 scores above 85%” | Removed numeric claim | No verified source in repo |
| STANet/BIT “reporting F1 scores in the 87–89% range” | Removed numeric claim | References unverified |
| “consistent with published results for comparable architectures” | Removed | No verified comparison |
| Sentinel-2 “approximately 5-day” revisit | Changed to “frequently revisited” | Not verified in repo |
| “13-band Sentinel-2 acquisitions” | Changed to “aligned to a common grid” | Evaluation uses five bands; band count not needed |
| “these methods … accuracy independent of spatial resolution” | Replaced with mixed-pixel limitation | Spectrum is diluted at 10 m |
| “resolution-agnostic spectral index” | Removed everywhere | Not supported |
| “isolating spatial resolution as the sole independent variable” | Replaced with “isolates the simulated factor” | Blur/resample omits real sensor differences |
| “attributable to resolution loss in isolation” | Removed | Not established for real Sentinel-2 |
| “under-studied” | Removed | Unsupported literature claim |
| “warehouse rooftops” explanation | Removed | No saved per-image visual evidence |
| “observed maximum confidence below 1%” | Removed | No probability arrays saved |
| “initial testing … obvious construction” as evidence | Reframed as uncontrolled internal observation, not used as evidence | No saved record |
| “full quantitative comparison … is ongoing” | Replaced with the saved OSCD v2 results | The comparison exists in saved data |

### 10. New section: real Sentinel-2 evaluation

A new Section V adds only values that are present in `oscd_results_v2.json`:

- pooled test set: 10 cities, 3,077,936 pixels, true change 5.17%;
- pooled F1: hardcoded 0.0782, percentile 0.1176, Otsu 0.0953, CNN joint-percentile
  0.0007, CNN reflectance 0.0000;
- predicted fractions: 2.24%, 1.66%, 67.35%, 0.01%, 0.00%;
- Otsu recall 0.6684, precision 0.0513, OA 0.3439;
- CNN OA 0.9483, described as close to the 94.83% no-change prevalence, not as
  detection performance;
- per-city ranges from the saved rows.

The section also states exactly how OSCD bands become CNN input, as read from
`benchmarks/oscd_eval.py` and `tiling.py`:

- RGB only: B04, B03, B02; B08 and B11 are used only for NDVI/NDBI;
- reflectance variant: raw values `/ 10000 * 255`, clipped to 0–255;
- joint-percentile variant: 2nd/98th percentiles over both dates combined, mapped to
  0–255;
- 256×256 tiles with 32-pixel overlap, edge padding, averaged probabilities; no scene
  resizing in `oscd_eval.py`.

### 11. Protocol and scoring history

The revised draft discloses:

- the ten official test cities were scored more than once;
- an earlier preliminary run with a smaller threshold grid produced pooled F1 0.167
  (percentile), 0.104 (hardcoded), 0.095 (Otsu) and 0.0 (CNN);
- the total number of scoring events is not recorded;
- v2 is a re-evaluation after train-only configuration selection, not an independent
  first test;
- no “one-shot” claim is made;
- the repository's `PREREGISTRATION.md` was written after earlier scoring and is not
  used as evidence of pre-registration or validation.

Evidence: `PAPER_NOTES.md` lines 1–6 and 74–80; user instruction for this step.

### 12. Remaining unverified items

- The reference list is unverified. It contains duplicate STANet entries ([1] and [4]).
  The FC-Siam citation details must be checked against the original publication. No
  DOI, volume or page was invented or corrected from memory.
- Author identity, department and `[author email address]` remain in the DOCX; remove
  or anonymise if the target venue uses double-blind review.
- City-level confidence intervals and threshold robustness are not in this draft; they
  are produced in Step 2 and added to the LaTeX paper.
- No LaTeX/PDF build was produced in this step; the DOCX is a corrected content copy,
  not a typeset submission.
