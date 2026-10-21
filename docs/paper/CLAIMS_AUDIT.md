# Claims audit

Audit date: 2026-10-21. Scope: every quantitative or comparative claim in
`paper.tex`, plus the claims a reader might infer from the abstract and
figures. Source of record: `benchmarks/results/oscd_results_v2.json`
(SHA-256 `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f`).

Status meanings:

- **Supported** — reproduced from a tracked file in this checkout.
- **Partially supported** — the repository supports the wording, but an
  external fact or a stronger interpretation is not verified.
- **Unverified** — requires data, a model artifact or an external check that
  is absent here.
- **Not claimed** — explicitly excluded; must not appear as a result.

| ID | Claim (paper location) | Evidence | Status | Action |
|---|---|---|---|---|
| C1 | Official OSCD test split has 10 cities; 14 training cities are used for selection (Sec. III, V) | `benchmarks/oscd_eval.py` reads `train.txt`/`test.txt`, checks the official test list, and `PAPER_NOTES.md` records the split | Supported | Keep; cite the dataset protocol after verifying |
| C2 | Pooled true change is 5.17% (abstract, Sec. III, VI) | Sum of TP+FN over 3,077,936 pooled test pixels = 5.17%; `oscd_results_v2.md` | Supported | Keep |
| C3 | Percentile rule: pooled precision 0.2419, recall 0.0777, F1 0.1176 (abstract, Sec. VI) | Recomputed from the v2 JSON confusion counts; matches v2 Markdown | Supported | Keep |
| C4 | Hardcoded rule: pooled F1 0.0782; predicted 2.24% (abstract, Sec. VI) | Recomputed from v2 JSON; matches v2 Markdown | Supported | Keep |
| C5 | Otsu: predicted 67.35%, OA 0.3439, precision 0.0513, recall 0.6684, F1 0.0953 (abstract, Sec. VI) | Recomputed from v2 JSON; v2 Markdown reports OA as the headline | Supported | Keep the OA caveat in every caption |
| C6 | CNN joint-percentile: predicted 0.01%, pooled F1 0.0007; reflectance 0.00%, F1 0.0000 (abstract, Sec. VI) | Recomputed from v2 JSON; per-city values in v2 Markdown | Supported | Keep |
| C7 | CNN joint-percentile overall accuracy is 0.9483, slightly above spectral OA (Sec. VI) | Recomputed from v2 JSON | Supported | Keep, but do not call it an improvement |
| C8 | Percentile per-city F1 ranges 0.0005–0.2481; hardcoded 0.0032–0.3102 (Sec. VI) | v2 JSON and Markdown per-city rows | Supported | Keep |
| C9 | Thresholds selected on the 14 training cities only; test labels not used for fitting (Sec. V) | `benchmarks/oscd_eval.py` `select_configs` reads training cities before scoring; v2 notes | Partially supported | A code-path check supports it; no independent audit of every historical run exists |
| C10 | Hardcoded selected NDVI −0.30 and NDBI +0.30 lie at the grid edge (Sec. IV, Discussion) | `PAPER_NOTES.md`; grid definitions in `benchmarks/oscd_eval.py` | Supported | Keep |
| C11 | Percentile selected 99.0 (Sec. IV) | `PAPER_NOTES.md`; v2 selection metadata | Supported | Keep |
| C12 | Two test-scoring events preceded this paper; preliminary pooled F1 values were percentile 0.167, hardcoded 0.104, Otsu 0.095, CNN 0.0 (Sec. V) | `PAPER_NOTES.md` disclosure paragraph | Supported by project record | Keep the disclosure; do not present the preliminary run as independent |
| C13 | v3 was preregistered and has no result file in this checkout (Sec. V, VII) | `docs/paper/PREREGISTRATION.md`; `benchmarks/results/` contains only v2 files | Supported | Keep; recheck before submission |
| C14 | The 12-system validation search uses leave-one-city-out training folds and refuses official test cities (Sec. V, VII) | `benchmarks/auto_improve.py`; `tests/test_auto_improve.py` | Supported as implemented | Do not call it a validation result; it was not run |
| C15 | No ablation/calibration values are reported (Sec. VII) | No `auto_improve_log.json`, uncertainty JSON or v3 file is present | Supported | Keep placeholders; run Colab before adding any value |
| C16 | The learned per-pixel classifier has no test score here and is disabled by default (Sec. VII) | `learned_pipeline.py`; `.env.example`; absent joblib artifact | Supported | Keep |
| C17 | The provided CNN checkpoint is described as trained on 0.5 m LEVIR-CD aerial pairs (Sec. III) | `README.md`; checkpoint absent from this checkout, so the description cannot be independently checked | Partially supported | Cite the dataset; do not imply the weights were re-verified here |
| C18 | A domain gap is a plausible explanation, not a causal finding (Sec. VIII) | `PAPER_NOTES.md` uses the same hypothesis wording; no controlled experiment | Supported as a hypothesis | Never upgrade to "caused by" |
| C19 | No SCL in the benchmark layout, so cloud/shadow masking is not evaluated (Sec. III, IX) | `PAPER_NOTES.md`; `benchmarks/oscd_eval.py` sets `use_cloud_mask=False` | Supported | Keep |
| C20 | v2 uses no MMU, compositing, PIF or cleanup (Sec. IV) | `benchmarks/oscd_eval.py` `spectral_prediction` only thresholding; v2 configs | Supported | Keep |
| C21 | Figure generator rejects partial city/method coverage and writes a hash manifest (Sec. X) | `scripts/make_paper_figures.py`; `tests/test_paper_figures.py`; `figure_manifest.json` | Supported | Keep |
| C22 | The interface shows no accuracy number for unvalidated profiles (Sec. VIII) | `profiles/validation_status.json`; UI rendering in `static/app.js` | Supported by code/tests | Keep |
| C23 | The app has no authentication and history stores previews/locations (Sec. IX) | `app.py` routes; `history_store.py`; `docs/LIMITATIONS.md` | Supported | Keep; legal/privacy review required before public deployment |
| C24 | OSCD labels are CC BY-NC-SA as recorded in project notes (Sec. X) | `PAPER_NOTES.md` / project notes only | Unverified externally | Verify the dataset licence text and obtain legal review |
| C25 | LEVIR-CD, Sentinel-2, NDVI/NDBI, Otsu, cross-sensor transfer, test-set reuse, preregistration, spatial CV and calibration descriptions | No verified bibliography yet; placeholders only | Unverified | Complete `TODO_CITATIONS.md`; do not submit with placeholders |
| C26 | "Targeting or enforcement" exclusion and human-verification requirement (Sec. X) | Project scope and UI wording; ethical judgement | Supported as a scope statement | Keep |
| C27 | The code commit used for the v2 numbers is the Phase E commit recorded in history | Local Phase E commit `a6dad9e`; later Phase F changes are documentation/figures/tests | Partially supported | Verify final commit and state it in the submitted version |
| C28 | Related work positions the work without a priority claim (Sec. II) | `paper.tex`; `NOVELTY_CHECKLIST.md` | Supported as wording; novelty unverified | Keep the hedged wording; complete the external search before any change |
| C29 | Future work lists human feedback, labelled non-urban data, higher-resolution roads and unfinished D2 items (Sec. VIII, Future Work) | `paper.tex`; `FUTURE_WORK.md` | Supported as a scope statement | Keep; do not describe any item as planned, funded or started |
| C30 | The paper's contributions are an auditable implementation, a train-only benchmark with disclosed history, and an uncomputed preregistered protocol (Sec. I) | Repository implementation, v2 files, `PREREGISTRATION.md` | Supported as scope/wording | Do not upgrade to method novelty or priority |

## Claims explicitly not made

- No priority, novelty or "first" claim. No statement that this is the best
  method, a state-of-the-art result or an improvement over published OSCD
  baselines.
- No accuracy claim for the `general`, `agriculture`, `deforestation` or `roads`
  profiles. The `builtup` profile is not claimed as separately validated; only
  the underlying spectral thresholding has a v2 score, for urban change.
- No cloud/shadow-mask accuracy claim.
- No causal claim about domain gap, resolution, season or preprocessing.
- No operational, safety-critical, legal or enforcement accuracy claim.
- No claim that fusion, compositing, PIF, cleanup, the learned classifier or
  the validation search improve test performance.
- No claim that ten cities are representative of global urban change.
- No commercial-use or redistribution permission for OSCD, Copernicus or OSM
  data; those require licence review.

## Numerical consistency checks

- JSON rows: 50 (10 cities × 5 configurations), all `split: "test"`.
- Pooled pixels: 3,077,936 for every configuration.
- JSON vs Markdown: pooled F1, precision, recall, predicted fraction and OA
  agree to four decimals for all five configurations.
- Figure/table generator: recomputes pooled values from confusion counts; it
  fails on missing methods, duplicate city/method rows, non-test rows or
  unknown pipelines.
- Source hash is written to `docs/paper/figures/figure_manifest.json`; no
  figure or table is generated from a different input in this checkout.
