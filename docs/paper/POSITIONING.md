# Positioning against published work

This file is a placeholder for a verified comparison table. It is deliberately
empty: no published method has been entered because no bibliography has been
verified. The paper's related work uses `[CITE: ...]` slots, and the reference
work list is in `REFERENCES_TO_VERIFY.md`.

Do **not** fill a row from memory, from a secondary summary, or from the
approximate values in `README.md`. Open the original paper or publisher page,
record the exact protocol, and only then add the row. If the protocol differs,
mark the comparison as not comparable rather than adjusting the number.

## Published-method table

`TODO - fill from original paper` for every cell.

| Work (verified citation key) | Sensor / native resolution | Training data | Test data and split | Task / label definition | Metric and definition | Reported value | Comparable to this paper? | Source checked |
|---|---|---|---|---|---|---|---|---|
| TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | No |
| TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | No |
| TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | No |
| TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | No |
| TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | No |
| TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | TODO - fill from original paper | No |

## What this paper measures (for later comparison)

These are the paper's own saved values, not published baselines. They are
listed here so a future comparison table has the correct protocol columns.

| Setting | Protocol | Metric | Value | Source |
|---|---|---|---|---|
| Frozen CNN, LEVIR-CD test, native 0.5 m | 2,048 pairs, 256×256, threshold 0.5 | Pooled F1 / IoU | 87.06% / 77.08% | `degradation_results.csv` |
| Frozen CNN, simulated 1 m | Blur + LANCZOS downsample/upsample | Pooled F1 | 70.81% | same |
| Frozen CNN, simulated 2 m | same | Pooled F1 | 4.41% | same |
| Frozen CNN, simulated 10 m | same; 12×12 intermediate | Pooled F1; predicted fraction | 2.61%; 0.068% | same |
| Frozen CNN, OSCD test, joint percentile | Zero-shot, RGB, 256 tiles, 32 overlap | Pooled F1 | 0.0007 | `oscd_results_v2.json` |
| Frozen CNN, OSCD test, reflectance | Zero-shot, RGB, 256 tiles, 32 overlap | Pooled F1 | 0.0000 | same |
| Hardcoded NDVI/NDBI, OSCD test | Train-selected −0.30/+0.30 | Pooled F1 | 0.0782 | same |
| Percentile 99.0, OSCD test | Train-selected percentile | Pooled F1 | 0.1176 | same |
| Otsu, OSCD test | Unsupervised threshold | Overall accuracy | 0.3439 | same |

The OSCD values are descriptive scores on a test split that had been scored
before the reported run. They are not leaderboard entries.

## Rules for a defensible comparison

1. Compare only on the same dataset, split, label definition, metric and
   preprocessing. If any of these differ, write “not comparable” and explain
   why.
2. Record the original paper's exact reported number and the table or section it
   came from. Do not round or convert metrics unless the original paper does.
3. For datasets, use the dataset's own paper and licence page. For metrics,
   prefer the definition in the original method paper or the benchmark protocol.
4. Do not infer a published method's performance from a survey, a blog, a
   secondary table, or this repository's README.
5. Add every new source to `REFERENCES_TO_VERIFY.md`; a row is not usable until
   the source is checked.
6. The paper's contribution is the resolution-mismatch evidence and the
   reporting discipline, not a ranking. A comparison table, if added, should
   support that framing rather than turn the paper into a leaderboard claim.

## Why the table is empty now

- No verified bibliography exists; the manuscript has 15 `[CITE: ...]` slots.
- The legacy README lists candidate entries (including an arXiv identifier and a
  DOI) but those records have not been checked against publisher pages.
- The original DOCX reference list contains duplicate STANet entries and an
  FC-Siam entry that must be checked against the original publication. See
  `REFERENCES_TO_VERIFY.md`; do not resolve the duplication from memory.
- Filling this table before verifying sources would create exactly the kind of
  unsupported comparison the paper is trying to avoid.
