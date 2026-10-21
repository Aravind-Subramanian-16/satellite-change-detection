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
| Train-only LOCO script | `benchmarks/oscd_loco_thresholds.py` | Present; result from the Colab run (training cities only) |
| LOCO result | `benchmarks/results/oscd_loco_thresholds.json` | Present; 14 training cities; no test label read |
| Model check | `benchmarks/results/colab_model_check.json` | Present; Drive `model.onnx` size/SHA-256 and onnxruntime load |
| Colab hand-off | `notebooks/run_all_colab.ipynb`, `benchmarks/colab_run_summary.py` | Run on Colab 2026-10-21 at `e8b6678` |
| Colab summary | `benchmarks/results/COLAB_RUN_SUMMARY.md` | Present; generated from the saved LOCO and model-check JSON |
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
137 passed, 3 skipped, 1 warning
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
| `benchmarks/results/oscd_loco_thresholds.json` | `32d1dbf57d83a1c68c76de0d64856795c082498788428c8206fd7cf2a4a2e29d` |
| `benchmarks/results/colab_model_check.json` | `ec452724a09c915a6577b535146bd78fe5f09dd9ce13421d8359057709c3902a` |
| `benchmarks/results/COLAB_RUN_SUMMARY.md` | `77177c595f2a80aa71c3e9d5ff2dc9b31bf7b976a5a909e1a58152507dffeca6` |
| `docs/paper/figures/figure_manifest.json` | `b0a1e80547dcfc0b171008d266a456e250f0e3db3c226e5cb1a41f1140055680` |
| `docs/paper/paper.tex` | `d6ab6330ea94c9cc2a6b4b185bddf1ce98e8e7fa52a7051ef6751f08c589a767` |

The manifest and manuscript hashes are snapshots; they change when those files
are regenerated or edited. The test-set source-of-record files are the
degradation CSV and the v2 JSON; the LOCO JSON is a separate training-only
source. These files must not change for the paper's numbers to remain valid. The
manifest records the test-set source hashes used at generation time.

## 5. Seeds and run configuration

- City-bootstrap intervals and paired differences: seed 0, 10,000 resamples
  (`benchmarks/oscd_evidence.py`, `scripts/make_paper_figures.py`).
- Threshold selection: deterministic fixed grids on the 14 training cities; no
  random seed is used by the grid search.
- Leave-one-city-out robustness: one fold per training city (14 folds), the same
  deterministic grids, no random seed; official test cities are rejected before
  any raster is read.
- Model check: size, SHA-256 and onnxruntime load on the Colab CPU runtime; no
  inference is run.
- CNN training: one run, configured for up to 100 epochs with early stopping;
  stopped after 27 epochs, best validation IoU 0.7205. **The training seed is not
  recorded in the paper or the training log**, and no seed variation was run.
- CNN inference: fixed checkpoint and threshold 0.5; no test-time augmentation.
- Degradation factors: 1, 2, 4, 8, 16, 20 (0.5, 1, 2, 4, 8, 10 m).

## 6. What not to run for this paper

- **Do not run `benchmarks/oscd_eval.py` on the test cities.** Doing so would add
  another test-scoring event and contradict the paper's disclosure and scope.
- **Do not run `benchmarks/oscd_loco_thresholds.py` against test cities.** It is
  a train-only procedure and rejects official test cities. Its saved result is
  the training-only robustness check reported in the paper; it is not a test
  score and must not be rerun on the test split.
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
the v2 numbers correspond to a different commit. The push blocker was resolved
on 2026-10-21 by switching the client to HTTP/1.1; the remote `main` then
contained all prior commits through `e8b6678`. The Step 7b documentation commit
is local until the owner pushes it. Do not force push or rewrite history.

## 8. Colab

The one-click `notebooks/run_all_colab.ipynb` was run on a fresh Colab runtime
on 2026-10-21 at commit `e8b6678`. It mounted Drive, unzipped only the
images/training-labels archive, pulled the repository, copied the Drive weights,
installed benchmark dependencies, ran pytest, ran the train-only LOCO script,
checked the Drive `model.onnx` size/SHA-256 and onnxruntime load, and wrote
`benchmarks/results/COLAB_RUN_SUMMARY.md`. It did not unzip `test_labels.zip`,
score a test city, train, fine-tune or run v3.

Saved outputs:

| File | Result |
|---|---|
| `benchmarks/results/COLAB_RUN_SUMMARY.md` | Colab pytest `144 passed, 1 skipped, 7 warnings in 15.79s` (exit 0); scope statements; SHA-256 `77177c59...` |
| `benchmarks/results/oscd_loco_thresholds.json` | 14 training cities; hardcoded pooled held-out F1 0.0976, percentile 0.1469; hardcoded grid-edge in 14/14 folds, percentile 0/14; no test city in `train.txt`; no test-label path accepted; SHA-256 `32d1dbf5...` |
| `benchmarks/results/colab_model_check.json` | 33,268,410 bytes; SHA-256 `41c2ab64...`; onnxruntime load `true`; inputs `input_a`, `input_b`; SHA-256 `ec452724...` |

The Colab pytest count differs from the local count because the Colab runtime
has `rasterio`, `torch` and the dataset sample, so fewer tests skip. The
training-only LOCO values are descriptive robustness numbers, not test scores.

The other two notebooks remain unrun:

- `notebooks/oscd_pixel_classifier.ipynb` — learned pixel classifier; not run,
  no pasted output.
- `notebooks/oscd_auto_improve.ipynb` — validation-only search; not run, no
  pasted output.

`GITHUB_TOKEN` handling for a Colab push: read it from Colab Secrets into
memory, never print it, never write it to disk or the notebook output, and never
commit it. The token is passed to git only through a temporary
`GIT_CONFIG_VALUE` environment variable. If it is missing or the push fails,
the notebook prints exactly `Push skipped: copy the block above`. Do not paste
secrets into chat.

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

## 10. Status of remaining items

| Item | Status | What is needed |
|---|---|---|
| PDF build and four-page limit | Unverified | Compile on Overleaf with IEEEtran; check page count excluding references |
| Bibliography | Not present | Replace 15 `[CITE: ...]` slots with verified records |
| v2 benchmark re-execution | Not possible here | OSCD imagery/labels and the checkpoint |
| CNN inference re-execution | Not possible here | `best_model.pt` / valid local `model.onnx` |
| Train-only LOCO result | Present, training-only | 14 training folds; no test label read; do not treat as a test score |
| One-click Colab notebook | Run 2026-10-21 at `e8b6678` | No test city scored; do not rerun against test labels |
| Colab run summary | Present | Generated from the saved LOCO and model-check JSON |
| Model size/SHA-256/load | Verified on Colab | Local real inference still unverified |
| Learned classifier and auto-improve notebooks | Not run | Optional paused experiments; no results |
| Docker image | Unverified | Docker unavailable locally |
| GitHub Actions | Unverified | Confirm the workflow run on GitHub after the successful push |
| OSCD licence | Unverified externally | Official licence page and legal review |
| Author email / final metadata | Unverified | Owner confirmation |
| Code licence | Not chosen | Owner decision |

## 11. Owner actions

1. Push the Step 7b commit without force; do not rerun the Colab notebook on the
   test split.
2. Place the verified 33,268,410-byte checkpoint (SHA-256 `41c2ab64...`,
   inputs `input_a` / `input_b`) in the local checkout and run a real `/predict`
   pair; the Drive file is verified, but local inference is not.
3. Do not rerun `notebooks/run_all_colab.ipynb` against test labels. It is a
   training-only hand-off; its saved output is already recorded.
4. Make OSCD imagery and labels available in the expected layout if a rerun is
   required; do not score the test cities again for this paper.
5. Compile `docs/paper/paper.tex` on Overleaf; check the four-page limit
   excluding references; add the bibliography after verifying every source.
6. Confirm the author block and whether the venue requires anonymisation.
7. Choose a code licence if one is desired; none is chosen here.
8. Obtain legal review for OSCD, Copernicus and OSM terms.
