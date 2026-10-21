# Artifact and reproduction guide

This guide describes what the repository contains, what can be reproduced from
this checkout, and what is missing. It does **not** claim that the benchmark
can be re-executed here: the imagery and the checkpoint are absent.

## 1. What is included

| Component | Path | Status |
|---|---|---|
| Manuscript source | `docs/paper/paper.tex` | Present; not compiled |
| Generated figures | `docs/paper/figures/fig_f1_vs_resolution.png`, `fig_oscd_per_city_and_fractions.png` | Present |
| Generated tables | `docs/paper/figures/generated_degradation_table.tex`, `generated_oscd_table.tex` | Present |
| Figure manifest | `docs/paper/figures/figure_manifest.json` | Present |
| Degradation evidence | `degradation_results.csv` | Present; 12,288 rows |
| OSCD v2 results | `benchmarks/results/oscd_results_v2.json` / `.md` | Present; not re-scored |
| Derived OSCD evidence | `benchmarks/results/oscd_evidence.json` / `.md` | Present; derived from v2 |
| Figure/table generator | `scripts/make_paper_figures.py` | Present; tested |
| Degradation runner | `evaluate_degradation.py` | Present; cannot run without data/weights |
| OSCD evidence script | `benchmarks/oscd_evidence.py` | Present; reads saved JSON only |
| Train-only LOCO script | `benchmarks/oscd_loco_thresholds.py` | Present; real result pending Colab |
| Web application | `app.py`, `static/`, `live_pipeline.py` | Runs locally; not validated end to end |

Not included: LEVIR-CD imagery and labels, OSCD imagery and labels, the CNN
checkpoint (`best_model.pt` / `model.onnx`), and any joblib model artifact.

## 2. Environment

Recorded on 2026-10-21:

- macOS Darwin 21.6.0 on x64, Python 3.10.0.
- Dependencies are ranges in `requirements.txt`, `requirements-dev.txt`,
  `requirements-benchmark.txt` and `requirements-train.txt`; there is no
  lockfile.
- `rasterio` and `torch` are not installed in the local runtime environment;
  Docker is not installed.

Use a virtual environment and `python -m pip`:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## 3. Reproduce the saved analysis

The paper's figures and tables are generated only from the two saved files:

```bash
./venv/bin/python scripts/make_paper_figures.py \
  --results benchmarks/results/oscd_results_v2.json \
  --degradation degradation_results.csv \
  --out docs/paper/figures \
  --seed 0 \
  --resamples 10000
```

This writes the two figures, the two tables and `figure_manifest.json`. It does
not read imagery and does not score a city.

Recompute the OSCD baselines, city-bootstrap intervals and paired differences:

```bash
./venv/bin/python benchmarks/oscd_evidence.py \
  --input benchmarks/results/oscd_results_v2.json \
  --json-output benchmarks/results/oscd_evidence.json \
  --md-output benchmarks/results/oscd_evidence.md \
  --seed 0 \
  --resamples 10000
```

Run the tests:

```bash
./venv/bin/python -m pytest -q
```

Expected on this checkout:

```text
128 passed, 3 skipped, 1 warning in 10.35s
```

Runtime varies. The skips are the Pipeline A regression (needs weights and a
dataset sample), the OSCD label tests (need `rasterio`), and the torch-only crop
dataset test. A Starlette test-client deprecation warning is emitted.

## 4. Saved inputs and hashes

| File | SHA-256 |
|---|---|
| `degradation_results.csv` | `4c301920d03d09dbc416d82fa76b93e76e1fab9b74bc2db5155da9735965fa88` |
| `benchmarks/results/oscd_results_v2.json` | `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f` |
| `benchmarks/results/oscd_results_v2.md` | `b3033c59064a1c5f9b2c9efccc8ecfed595c186ba9aed6369dc15a29753ec738` |
| `benchmarks/results/oscd_evidence.json` | `3d7f19bab34e9a524bd75036fcfcafaa4a44f453f145cc4611e9762643d81d71` |
| `benchmarks/results/oscd_evidence.md` | `693e2f77b3fa93cd82d982a3ac5c88a4fa6759386aa00aff7379fc30fe0ebcdf` |
| `docs/paper/figures/figure_manifest.json` | `b26a0c3e3531fa4b0b8b3cd665c3a37e77b6b9b5d14f0d857701c8995e660c7e` |
| `docs/paper/paper.tex` | `095fd4d3416ae9c31f570f3ac55de2a3748c5d861863dcf5b5174dafd10582d1` |

The manifest and manuscript hashes are snapshots; they change when those files
are regenerated or edited. The two source-of-record files must not change for
the paper's numbers to remain valid. The manifest records the source hashes used
at generation time.

## 5. Seeds and run configuration

- City-bootstrap intervals and paired differences: seed 0, 10,000 resamples
  (`benchmarks/oscd_evidence.py`, `scripts/make_paper_figures.py`).
- Threshold selection: deterministic fixed grids on the 14 training cities; no
  random seed is used by the grid search.
- CNN training: one run, configured for up to 100 epochs with early stopping;
  stopped after 27 epochs, best validation IoU 0.7205. **The training seed is not
  recorded in the paper or the training log**, and no seed variation was run.
- CNN inference: fixed checkpoint and threshold 0.5; no test-time augmentation.
- Degradation factors: 1, 2, 4, 8, 16, 20 (0.5, 1, 2, 4, 8, 10 m).

## 6. What not to run for this paper

- **Do not run `benchmarks/oscd_eval.py` on the test cities.** Doing so would add
  another test-scoring event and contradict the paper's disclosure and scope.
- **Do not run `benchmarks/oscd_loco_thresholds.py` against test cities.** It is
  a train-only procedure and rejects official test cities; its real result is
  pending a Colab run and is not part of the paper.
- **Do not retrain, fine-tune or modify `best_model.pt` or `model.onnx`.**
- **Do not generate a synthetic result file** to fill a missing number. The
  figure generator is tested against fake JSON only in the test suite.

## 7. Commits

The paper artifacts are in commits:

- `f317d89` — correct 10 m IoU bins in the revised DOCX and log;
- `730b025` — figure/table generator and generated assets;
- `33146c4` — IEEEtran manuscript;
- `c6c3d5a` — Step 3 progress evidence.

The v2 scorer code is recorded as Phase E commit `a6dad9e`; later commits add
documentation, figures, tests and new analysis scripts, but they do not change
the v2 result files. Verify this with `git log -- benchmarks/` before claiming
the v2 numbers correspond to a different commit. The local branch may be ahead of `origin/main`; the push
attempt for these commits failed with HTTP 400, so the remote may not contain
them. Do not force push or rewrite history.

## 8. Colab

Existing notebooks:

- `notebooks/oscd_pixel_classifier.ipynb` — learned pixel classifier; not run,
  no pasted output.
- `notebooks/oscd_auto_improve.ipynb` — validation-only search; not run, no
  pasted output.

The one-click `notebooks/run_all_colab.ipynb` is the Step 7 deliverable and is
not present at this commit. Colab runs must not score the official test cities
for the learned classifier or the validation search. For the LOCO threshold
check, the procedure is train-only and its real output is pending.

`GITHUB_TOKEN` handling for a Colab push: read it from Colab Secrets into
memory, never print it, never write it to disk or the notebook output, and never
commit it. If it is missing or the push fails, print exactly
`Push skipped: copy the block above`. Do not paste secrets into chat.

## 9. Licences and legal review

- **No code licence has been chosen.** There is no `LICENSE` file; do not add
  one on the owner's behalf.
- OSCD is recorded in project notes as **CC BY-NC-SA**. This has not been
  verified externally and may restrict commercial use. Verify the licence text
  at the dataset's official page and obtain legal review before redistribution
  or commercial use.
- Copernicus Sentinel data has its own terms and attribution requirements;
  verify them before redistribution.
- OpenStreetMap context data is ODbL; attribution and share-alike obligations
  apply.
- The repository does not redistribute OSCD imagery, LEVIR-CD imagery or the
  model checkpoint.

## 10. Unverified items

| Item | Status | What is needed |
|---|---|---|
| PDF build and four-page limit | Unverified | Compile on Overleaf with IEEEtran; check page count excluding references |
| Bibliography | Not present | Replace 15 `[CITE: ...]` slots with verified records |
| v2 benchmark re-execution | Not possible here | OSCD imagery/labels and the checkpoint |
| CNN inference re-execution | Not possible here | `best_model.pt` / valid `model.onnx` |
| Train-only LOCO result | Pending | Colab run; do not guess values |
| One-click Colab notebook | Not yet created | Step 7 deliverable |
| Docker image | Unverified | Docker unavailable locally |
| GitHub Actions | Unverified | Push blocked by HTTP 400 |
| OSCD licence | Unverified externally | Official licence page and legal review |
| Author email / final metadata | Unverified | Owner confirmation |
| Code licence | Not chosen | Owner decision |

## 11. Owner actions

1. Supply the verified model checkpoint and confirm input names `input_a`,
   `input_b`; do not replace it with the invalid local ONNX file.
2. Make OSCD imagery and labels available in the expected layout if a rerun is
   required; do not score the test cities again for this paper.
3. Compile `docs/paper/paper.tex` on Overleaf; check the four-page limit
   excluding references; add the bibliography after verifying every source.
4. Confirm the author block and whether the venue requires anonymisation.
5. Choose a code licence if one is desired; none is chosen here.
6. Obtain legal review for OSCD, Copernicus and OSM terms.
7. Resolve the push failure from the owner terminal with `git push origin main`;
   do not force push.
