# Artifact and reproduction guide

> **Evidence status (2026-10-22).** Reported aggregate metrics and paper
> tables can be derived from saved per-image/per-city counts. The source
> imagery, labels and CNN checkpoint are not included, so this checkout cannot
> rerun model inference or independently reproduce the original benchmark
> scoring events.

This guide distinguishes derivation of saved results from a full reproduction
of the experiments. It also documents the current application, which is
separate from the historical offline benchmark pipeline.

## 1. Included artifacts

| Component | Path | Status |
|---|---|---|
| Manuscript source | `docs/paper/paper.tex` | IEEEtran LaTeX source |
| Compiled draft | `docs/paper/paper.pdf` | Five-page PDF built with Tectonic 0.17.0; first page rendered for visual review; venue page limit and full-page inspection remain |
| Conference report | `docs/paper/CONFERENCE_READINESS.md` | Current submission blockers and scope |
| Claims audit | `docs/paper/CLAIMS_AUDIT.md` | Numerical evidence audit; some older implementation references require archival review |
| Degradation counts | `degradation_results.csv` | Present; 12,288 rows for 2,048 pairs × 6 factors |
| OSCD v2 confusion counts | `benchmarks/results/oscd_results_v2.json` | Present; 50 records for 10 cities × 5 configurations |
| Derived OSCD metrics | `benchmarks/results/oscd_evidence.json` / `.md` | Derived from saved v2 confusion counts; not new scores |
| Train-only LOCO results | `benchmarks/results/oscd_loco_thresholds.json` | Saved 14-training-city robustness results; not test results |
| Figure/table generator | `scripts/make_paper_figures.py` | Generates tables, figures and a source-hash manifest from saved results |
| OSCD evidence generator | `benchmarks/oscd_evidence.py` | Derives pooled metrics and bootstrap evidence from saved confusion counts |
| Benchmark evaluation code | `benchmarks/oscd_eval.py`, `evaluate_degradation.py` | Source is present; execution requires unavailable imagery/labels and checkpoint |
| Training/source code | `train.py`, `model.py`, `dataset.py`, `spectral_pipeline.py`, `tiling.py` | Historical offline experiment code; not the current browser application |
| Saved Colab report | `benchmarks/results/COLAB_RUN_SUMMARY.md` | A saved run summary; its notebook and runtime are not included in this checkout |
| Web application | `src/`, `server.ts` | React/TypeScript and Express RGB-screening application; not the benchmarked CNN |

Absent inputs include LEVIR-CD imagery and labels, OSCD imagery and labels, the
CNN checkpoint (`best_model.pt` / `model.onnx`), and the historical Colab
notebook. No benchmark image or model output should be synthesized to replace
these missing inputs.

## 2. Re-derive the saved summaries

The figures and tables use the saved count files; these commands do not read
imagery and do not rescore a test city:

```bash
python scripts/make_paper_figures.py \
  --results benchmarks/results/oscd_results_v2.json \
  --degradation degradation_results.csv \
  --out docs/paper/figures \
  --seed 0 \
  --resamples 10000

python benchmarks/oscd_evidence.py \
  --input benchmarks/results/oscd_results_v2.json \
  --json-output benchmarks/results/oscd_evidence.json \
  --md-output benchmarks/results/oscd_evidence.md \
  --seed 0 \
  --resamples 10000
```

The benchmark utilities require the packages in `requirements-benchmark.txt`;
training/evaluation utilities that use PyTorch additionally use
`requirements-train.txt`. These files are dependency lists, not pinned
environment lockfiles. Do not run the evaluation scripts on OSCD test cities
for this manuscript: the paper discloses prior scoring, and the original
evaluation protocol is not independently reproducible from this checkout.

The reported degradation summaries were recomputed from the 12,288 rows
(2,048 pairs × 6 factors). The reported OSCD summaries and city-bootstrap
intervals were regenerated from the 50 saved per-city/configuration records
(10 cities × 5 configurations). These are arithmetic/derivation checks, not
independent validation of model predictions.

## 3. Source-record integrity

| File | SHA-256 |
|---|---|
| `degradation_results.csv` | `4c301920d03d09dbc416d82fa76b93e76e1fab9b74bc2db5155da9735965fa88` |
| `benchmarks/results/oscd_results_v2.json` | `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f` |
| `benchmarks/results/oscd_loco_thresholds.json` | `32d1dbf57d83a1c68c76de0d64856795c082498788428c8206fd7cf2a4a2e29d` |
| `benchmarks/results/colab_model_check.json` | `ec452724a09c915a6577b535146bd78fe5f09dd9ce13421d8359057709c3902a` |
| `benchmarks/results/COLAB_RUN_SUMMARY.md` | `77177c595f2a80aa71c3e9d5ff2dc9b31bf7b976a5a909e1a58152507dffeca6` |
| `benchmarks/results/oscd_evidence.json` | Regenerated in this checkout; calculate from the current file before release |
| `benchmarks/results/oscd_evidence.md` | Regenerated in this checkout; calculate from the current file before release |
| `docs/paper/figures/figure_manifest.json` | Records hashes of the saved count inputs used for generated outputs |

The source-record hashes are part of the audit trail. The derived files and
manuscript change as they are regenerated or edited; record their final hashes
for any eventual submission archive. The OSCD evidence script records
repository-relative paths for in-repository inputs rather than machine-specific
absolute paths.

## 4. Experiment boundaries

- The degradation factors are 1, 2, 4, 8, 16 and 20, corresponding to the
  manuscript's 0.5, 1, 2, 4, 8 and 10 m simulation. The operation is blur,
  downsampling and upsampling of the same LEVIR-CD RGB scenes; it is not a
  physical Sentinel-2 sensor simulation.
- The OSCD evaluation uses saved test-city confusion counts. The official test
  cities were scored before the reported v2 run, and the total scoring-event
  count is not recorded. Do not describe these metrics as an untouched or
  independent test.
- The LOCO artifact uses training cities only. It is a robustness check, not a
  test-set result.
- The generated figures/tables and bootstrap intervals derive from those
  saved counts. They do not recover missing imagery, predictions, training
  logs, or uncertainty from model training and threshold selection.
- The current application performs RGB difference screening and is not
  validated by these historical benchmark metrics.

## 5. Application and publication status

The current application is React/TypeScript plus Express. It compares provider
RGB imagery or uploaded RGB pairs; it is not the historical Python/CNN
evaluation system. Provider imagery may be a mosaic whose acquisition date or
registration is uncertain. Generated fallback imagery is demonstration-only.
The app does not establish validated environmental classifications, physical
area measurements, or benchmark accuracy.

The manuscript has a bibliography with nine entries and no citation
placeholders. Bibliographic metadata has been checked, but the author must
verify source-to-claim wording and final reference formatting against the
publisher/official records before submission. `paper.pdf` was built with
Tectonic 0.17.0 using the IEEEtran class; its five pages and extracted text were
checked, and the first page was rendered for visual inspection. The exact IEEE
venue, track, deadline and required page limit are not yet specified. See
`CONFERENCE_READINESS.md` for remaining blockers.

No code licence has been selected. Dataset and provider-data terms have not
received legal review. Do not claim that the repository, data, checkpoint or
generated benchmark records are ready for unrestricted redistribution.
