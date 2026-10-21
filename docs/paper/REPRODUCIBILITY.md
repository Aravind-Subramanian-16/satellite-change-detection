# Reproducibility package (historical)

> **Superseded for the submission package.** This is a Phase F record of an
> earlier manuscript, test suite and figure generator. Use `ARTIFACT.md` for the
> current commands, hashes and owner actions, and `CLAIMS_AUDIT.md` for the
> current claims. The counts and hashes below are snapshots and may no longer
> match the checkout; the current paper does not include the v3 protocol or the
> earlier app-validation framing described here.

This document records what could and could not be reproduced at the Phase F
checkpoint, with commands, versions, hashes and owner actions. It refers to the
manuscript in `docs/paper/paper.tex` and the v2 result files.

## 1. Status at a glance

| Item | Status | Evidence |
|---|---|---|
| Web app, profiles, exports, reports | Runs locally | Live browser check; full test suite |
| Unit/integration test suite | 113 passed, 3 skipped, 1 warning (14.64 s; runtime varies) | `./venv/bin/python -m pytest -q` |
| Figure/table generation from saved JSON | Reproducible locally | `scripts/make_paper_figures.py`; manifest hash |
| v2 pooled/per-city numbers | Reproducible from tracked JSON (arithmetic checked) | `benchmarks/results/oscd_results_v2.json/.md` |
| v2 benchmark execution | **Not reproducible here** | OSCD imagery/labels absent |
| CNN inference in v2 | **Not reproducible here** | `model.onnx`/`best_model.pt` absent |
| Learned classifier training | **Unverified** | Training data/joblib absent; Colab not run |
| Auto-improvement search | **Unverified** | No `auto_improve_log.json` |
| v3 one-shot scoring | **Not run** | No `oscd_results_v3.*`; no scorer in checkout |
| Docker image | **Unverified** | Docker unavailable on this host |
| GitHub Actions CI | **Unverified** | Push now succeeds (HTTP/1.1, `e8b6678`); workflow result not checked from this checkout |
| LaTeX PDF build | **Unverified** | No `pdflatex`, `tectonic` or `latexmk` |
| Colab notebooks | `run_all_colab` run 2026-10-21 at `e8b6678` (summary and model check saved); learned/auto notebooks unverified | `benchmarks/results/COLAB_RUN_SUMMARY.md`; no output for the other two |

The skips are: the Pipeline A regression (needs `model.onnx` and a dataset
sample), OSCD label tests (needs `rasterio`, benchmark-only on this host), and
the torch-only crop-dataset smoke test.

## 2. Checkout state

- Repository root: the project directory containing `app.py`.
- Branch: local `main`, ahead of `origin/main` at the time of writing.
- Code commit for the v2 numbers and Phase E hardening: `a6dad9e`
  (`a6dad9e8c7ec6c4073e2b477a23a9160f77cdee6`). Phase F adds documentation,
  figures and tests; it does not change the benchmark code.
- `docs/paper/paper.tex` uses commit `a6dad9e` in its reproducibility section.
  If any benchmark code changes, this claim must be revisited.

### Source hashes

| File | SHA-256 |
|---|---|
| `benchmarks/results/oscd_results_v2.json` | `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f` |
| `benchmarks/results/oscd_results_v2.md` | `b3033c59064a1c5f9b2c9efccc8ecfed595c186ba9aed6369dc15a29753ec738` |
| `PAPER_NOTES.md` | `e0c0205ece2ce4e2a82529829eab69f952d81bf61ba2dfb7faf7c628487050a9` |
| `scripts/make_paper_figures.py` | `bd45534d3c74fd000fd81f61eefdf0c68119828c4c51b217dba1fe56a699a966` |
| `docs/paper/paper.tex` | `f2fc3c80ace352632eba97337f56f06a1428a6ddf8005471bc66697f423878df` |
| `docs/paper/figures/figure_manifest.json` | `e2514b3b3e58056a22657d65ec33460c7f80fd493d4cfcc662fb8a1a4157fc6d` |

The manifest is regenerated whenever figures are rebuilt; its own hash will
change. The manifest records the v2 JSON hash used at generation time. Paper
hashes change with edits; regenerate this table when the files change.

## 3. Environment

Recorded on 2026-10-21 from this checkout:

- macOS 12/21.x on x64 (Darwin 21.6.0), Python 3.10.0, pip 26.2.2.
- fastapi 0.156.3, numpy 2.2.6, scikit-learn 1.7.2, Pillow 11.3.0,
  reportlab 4.5.1, onnxruntime 1.19.2, matplotlib 3.10.9.
- `rasterio` and `torch` are **not installed**; Docker is **not installed**.

Dependency ranges are in `requirements.txt`, `requirements-dev.txt`,
`requirements-benchmark.txt` and `requirements-train.txt`. They are ranges,
not a lockfile; a future reproduction may resolve different patch versions.

## 4. Local setup and tests

Use a virtual environment and `python -m pip`:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Expected on this checkout:

```text
113 passed, 3 skipped, 1 warning in 14.64s
```

The warning is a Starlette test-client deprecation warning about `httpx`; it
does not fail the suite. Skips are environment-dependent and must remain skips,
not be silently removed.

Run the app:

```bash
./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8010
curl -fsS http://127.0.0.1:8010/health
```

`GET /health` returns a JSON status. Do not run `/predict` on the invalid
`model.onnx`; model-dependent endpoints return HTTP 503 until a valid
33,268,410-byte Drive copy is supplied.

`scripts/verify.sh` runs pytest plus health/prediction/PDF checks, but it
requires `dataset/test/A/test_100_0_0.png` and `dataset/test/B/test_100_0_256.png`,
which are **absent** from this checkout. It is therefore not a verified
reproduction step here.

## 5. Figures and tables

```bash
./venv/bin/python scripts/make_paper_figures.py \
  --results benchmarks/results/oscd_results_v2.json \
  --out docs/paper/figures
```

This is deterministic given the JSON and the matplotlib version. It:

1. requires exactly 10 test cities × 5 configurations (50 rows);
2. rejects duplicate `(city, method)` rows, unknown methods, non-test rows and
   incomplete city/method coverage;
3. computes pooled values from confusion counts, not by averaging F1;
4. writes `fig_per_city_f1.png`, `fig_predicted_vs_true.png`,
   `fig_precision_recall.png`, `fig_ablation.png`, `fig_reliability.png`,
   `fig_qualitative_placeholder.png`, three `.tex` tables and
   `figure_manifest.json`;
5. without an ablation/calibration input, writes *labelled placeholders* that
   say "not run" — it never estimates values.

Optional real inputs:

```bash
./venv/bin/python scripts/make_paper_figures.py \
  --ablation-log benchmarks/results/auto_improve_log.json \
  --calibration path/to/heldout_calibration.json \
  --out docs/paper/figures
```

The exact optional schemas are validated by `scripts/make_paper_figures.py`;
do not hand-write a log to make a figure appear.

Tests for the generator (fake JSON, strict rejection, manifest hashes):

```bash
./venv/bin/python -m pytest -q tests/test_paper_figures.py
```

## 6. Regenerating the v2 benchmark

**Do not run this casually.** `benchmarks/oscd_eval.py` writes/appends
`oscd_results_v2.json`, resumes by run key, and overwrites
`oscd_results_v2.md`. Re-running it on the official test split would be a new
test-scoring event, not a reproduction, and is prohibited by the project's
disclosure policy (`docs/paper/PREREGISTRATION.md`). If an independent
replication is intended, copy the v2 files and the original archive aside,
record hashes, and disclose the event.

The command used by the Colab notebook is:

```bash
python benchmarks/oscd_eval.py \
  --root /content/oscd \
  --output /content/drive/MyDrive/oscd/results
```

Requirements: OSCD images and train/test labels in the official directory
layout, `model.onnx` for the CNN rows, and `rasterio` (benchmark-only).
Thresholds are selected on the 14 training cities; the ten official test cities
are then scored. The notebook `notebooks/oscd_benchmark.ipynb` automates this
on Colab and copies results to Drive.

**Seed:** `oscd_eval.py` has no random seed; spectral rules are deterministic.
CNN inference depends on the checkpoint and runtime. The learned classifier and
auto-improvement use seed 42 in their notebooks.

## 7. Learned classifier and auto-improvement (owner-run Colab)

Both notebooks are written but **not run** here. Owner steps:

1. Upload the OSCD archive and weights to `My Drive/oscd/` as described in the
   notebook headers.
2. Run `notebooks/oscd_pixel_classifier.ipynb` on a fresh Colab CPU runtime.
   It installs `requirements-benchmark.txt`, verifies 14 training cities, runs
   the no-test-city guard, trains the 55-feature HistGradientBoosting model on
   11 cities, selects a threshold on 3 held-out training cities, and writes the
   joblib to Drive. **Paste the printed metadata into the project**; the joblib
   must stay outside git.
3. Run `notebooks/oscd_auto_improve.ipynb` on Colab. It runs the fixed 12
   systems × 14 leave-one-city-out folds, checkpoints every trial to
   `benchmarks/results/auto_improve_log.json`, and refuses test cities. Commit
   the resulting JSON/Markdown (no test rows) and **paste the summary**.
4. Do not run the v3 scoring event until the pre-registration's frozen inputs
   exist. The current checkout does not include a v3 scorer; it must be
   written and tested against the protocol **before** test access. This is a
   blocker, not a completed step.

Unverified claims that must remain unverified until output is pasted:

- held-out training accuracy of the learned classifier;
- calibration/ECE values;
- auto-improved system selection and component deltas;
- CNN fine-tuning results;
- any v3 test score.

## 8. Paper build

The manuscript uses IEEEtran conference class and generated tables. From
`docs/paper`:

```bash
pdflatex paper.tex
pdflatex paper.tex
```

A bibliography file is not yet present; citation slots are literal
`[CITE: topic]` placeholders. `TODO_CITATIONS.md` lists them. The build
requires `IEEEtran.cls`, `booktabs`, `longtable`, `amsmath`, `url`, `hyperref`
and `graphicx`.

**Not verified:** this host has no `pdflatex`, `tectonic` or `latexmk`.
Structural checks (balanced environments, existing inputs, no forbidden
priority phrases) were done by inspection/tests, but the PDF has not been
compiled. The owner must compile before submission and check page count,
figure placement, table widths and line breaks.

## 9. Data, licences and redistribution

- OSCD imagery and labels are **not** redistributed in this repository. The
  dataset is reported as CC BY-NC-SA; verify the current licence at the
  official source before any use. Non-commercial terms may prohibit commercial
  deployment.
- OSM tiles/Overpass data are used under ODbL with attribution; tile usage
  must follow the OSM tile policy.
- Copernicus Sentinel data are used under the Copernicus terms; credentials
  must stay in environment variables (`COPERNICUS_CLIENT_ID`,
  `COPERNICUS_CLIENT_SECRET`) and never be committed.
- The CNN checkpoint is not included. Its provenance (described as LEVIR-CD
  training) is owner-supplied and not independently verified here.

## 10. Unverified items and owner actions

| Item | Owner action |
|---|---|
| Invalid/missing `model.onnx` | Replace with the verified 33,268,410-byte Drive copy; confirm inputs `input_a`, `input_b` |
| Benchmark/CNN reproduction | Run `oscd_benchmark.ipynb` only as a disclosed event; preserve v2 files first |
| Learned classifier | Run the Colab notebook and paste output; record artifact SHA-256 |
| Auto-improvement | Run the Colab notebook; commit the log and paste the summary |
| v3 scoring | Implement/verify a protocol-compliant scorer before test access; run once; never tune |
| LaTeX build | Install TeX with IEEEtran; compile twice; inspect PDF |
| Docker | Build/run image; check `/health` and PDF export |
| CI | Confirm the workflow result on GitHub after the successful HTTP/1.1 push |
| Novelty | Verify externally; see `NOVELTY_CHECKLIST.md` |
| Licence | Legal review of OSCD/Copernicus/OSM terms before redistribution or commercial use |

## 11. What is genuinely reproducible now

Without OSCD data or weights, an independent reader can still:

- install the runtime and run 113 tests;
- start the app and exercise non-model endpoints with synthetic or mocked data;
- regenerate every paper figure and table from the tracked v2 JSON;
- recompute pooled metrics from the saved confusion counts;
- verify that the manuscript's numbers match the JSON;
- inspect the pre-registration and confirm that no v3 file exists;
- verify the absence of test-city reads in the training scripts by running the
  guard tests.

That is the intended scope of the reproducibility claim. It is not a claim
that the original benchmark or CNN inference can be re-executed from this
checkout.
