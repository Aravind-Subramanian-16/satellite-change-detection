# Candidate differentiators, evidence, and prior-work topics

Status: research planning document, 2026-10-21. This is **not** a priority
claim. No item here has been externally verified. The project must not make a
priority or superiority claim unless `NOVELTY_CHECKLIST.md` records a completed
search and the owner confirms the finding.

Legend: **implemented** = code and tests exist; **partial** = code or plan
exists but the claimed benefit is unmeasured; **idea** = not implemented.

| Candidate differentiator | Status | Local evidence | Evidence still required | Prior-work comparison topics |
|---|---|---|---|---|
| Live AOI → scene ranking → profile detection → PDF/GeoJSON provenance in one CPU-only app | implemented | `app.py`, `live_pipeline.py`, `scene_selection.py`, `reports.py`; network-free API tests; mocked UI screenshots | A real Copernicus end-to-end run with credentials, latency/error measurements, and a user study. Current UI evidence proves wiring only. | [CITE: operational satellite change-detection platforms]; [CITE: Sentinel-2 browser tools]; [CITE: decision-support interfaces for remote sensing] |
| Profile-specific honesty: no accuracy number is shown for unvalidated agriculture/deforestation/roads profiles | implemented | `profiles/validation_status.json`, `profiles/__init__.py`, Playwright assertion on the unvalidated badge | Whether users understand the distinction; a comprehension study. Also a validated dataset for each profile. | [CITE: uncertainty communication]; [CITE: trust and automation bias in decision support] |
| Train-only model selection with hard test-city guards and pre-registration | implemented | `learned_features.assert_no_test_cities`, `benchmarks/train_pixel_classifier.py`, `benchmarks/auto_improve.py`, `docs/paper/PREREGISTRATION.md` | Independent audit that the guard is sufficient; v3 run by the owner. Methodological value is not an empirical result. | [CITE: data leakage in machine learning]; [CITE: preregistration for ML experiments]; [CITE: benchmark overfitting] |
| Lightweight CPU per-pixel learned classifier (55 spectral/textural features) instead of a deep model | partial | `learned_features.py`, `learned_pipeline.py`, trainer; synthetic tests only | Train on OSCD TRAIN cities and report held-out TRAIN metrics; no test score exists yet. | [CITE: gradient-boosted trees for land-cover classification]; [CITE: pixel-wise change detection features]; [CITE: OSCD benchmark] |
| Optional radiometric PIF matching, temporal median compositing, morphology, and MMU | partial | `radiometric.py`, `compositing.py`, `postprocess.py`; new synthetic tests; UI/API flags default off | Paired train-city ablation (`auto_improve_log.json`) and a real multi-scene composite test. Current evidence is synthetic only. | [CITE: pseudo-invariant features for radiometric normalisation]; [CITE: temporal median compositing for Sentinel-2]; [CITE: minimum mapping unit effects] |
| Late fusion of spectral evidence and learned probability | partial | `fusion.py`; synthetic complementary-signal test | Fusion weights/threshold selected on held-out TRAIN cities and scoped v3 evaluation. No app route uses it. | [CITE: late fusion for remote-sensing change detection]; [CITE: ensemble stacking] |
| Model-agreement uncertainty with expected calibration error computed only on held-out TRAIN cities | partial | `uncertainty.py`; synthetic ECE/agreement tests | Real probabilities from trained models on held-out TRAIN cities; reliability diagram; no test-set calibration claim. | [CITE: calibration of neural networks]; [CITE: ensemble uncertainty in remote sensing] |
| OSCD-only CNN fine-tuning with a separate checkpoint and no touch to shipped weights | partial | `benchmarks/finetune_cnn.py`; guard/crop/threshold tests; torch smoke test skipped locally | Run on Colab/GPU; report held-out TRAIN metrics and the negative/positive result honestly. | [CITE: transfer learning for change detection]; [CITE: OSCD dataset] |
| Reproducibility metadata on every analysis and benchmark artifact | implemented | `provenance.py`, result JSON/MD, PDF provenance section; v2 metadata records commit and pytest line | A clean-machine reproduction and an audit of every reported number. | [CITE: reproducibility in remote-sensing research] |

## What is explicitly not claimed

- No priority or superiority claim is made for this application.
- No claim that profile outputs are accurate; agriculture, deforestation and
  roads are unvalidated and qualitative.
- No claim that PIF, compositing, fusion, uncertainty, or fine-tuning improve
  accuracy. They are implemented hypotheses; the validation log is the evidence.
- No claim that the v2 CNN result generalises; it is a measured negative result
  (pooled test F1 about 0.0007) on one benchmark.
- No claim that the test split has been used only once: `README.md` and
  `PAPER_NOTES.md` disclose the earlier preliminary test scoring event.

## Evidence plan

1. Train the learned model and fine-tuned CNN on the 14 TRAIN cities only
   (`notebooks/oscd_pixel_classifier.ipynb`, `benchmarks/finetune_cnn.py`).
2. Run `benchmarks/auto_improve.py` and keep its every-trial log, including
   failed trials. Selection is by pooled leave-city-out validation F1.
3. Freeze the selected systems in `docs/paper/PREREGISTRATION.md` before any
   test scoring.
4. Score the official test split once into `oscd_results_v3.json/.md`; never
   overwrite v2 and never re-select after seeing v3.
5. Report per-city variance and negative results. Do not report a pooled number
   without the per-city spread.
6. Complete `NOVELTY_CHECKLIST.md` searches before using any priority claim.
