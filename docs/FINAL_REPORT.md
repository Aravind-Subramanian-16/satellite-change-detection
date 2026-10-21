# Final Report — Satellite Change Detection

**Date:** 21 October 2026
**Branch:** `final-polish` (local only; not merged, not pushed)
**Final suite:** **194 passed, 3 skipped, 1 warning in 88.41 s** (earlier runs took 61.04 s post-dashboard and 42.00 s pre-dashboard)

This report closes Phases 0–5 of the redesign. It states what was delivered, the
exact test results, what is verified and what is not, and the commands to merge
and push. Everything below was measured in this checkout unless marked
otherwise.

---

## 1. What was delivered

| Area | Delivered | Main files |
|---|---|---|
| Friendly UI | Three-step wizard (area → dates → run), map and upload modes, goal picker, plain-English labels, dark/light theme, responsive layout to 375 px, data-quality badge with reasons, friendly network errors, keyboard focus styles | `static/index.html`, `static/app.js`, `static/app.css` |
| Analysis profiles | General, agriculture (loss **and** gain), deforestation, built-up, water, roads-as-context. Each carries a validation status; profiles add contextual warnings. Per-region "Why we think this changed" explanations | `profiles/`, `live_pipeline.py` |
| Results dashboard | Class table with area per change type, percentages, region counts; one source of truth shared by UI, CSV and PDF | `build_class_table` in `live_pipeline.py` |
| History dashboard | Client-side dashboard over saved analyses: count, live/upload split, simple mean and largest flagged share, per-analysis bars, range distribution, empty state. No API or database change | `static/index.html`, `static/app.js`, `static/app.css` |
| Reports | PDF with a one-page plain summary, badge, legend, class table, per-region reasons, provenance and credits; CSV; GeoJSON. New `GET /history/{id}/report` renders a stored analysis without re-posting it | `reports.py`, `app.py` |
| Robustness | Retries with backoff and `Retry-After` on transient Copernicus calls; bounded in-memory scene cache (64 MB / 32 entries, per process); `/health` reports CNN and spectral availability; history routes rate-limited; composite crash fixed when extended indices are absent | `copernicus_client.py`, `compositing.py`, `security.py` |
| Deployment docs | Cloud Run guide using Secret Manager; the pre-existing Dockerfile already excludes weights; no credentials baked in | `DEPLOY.md`, `Dockerfile` (pre-existing), `render.yaml` |
| User documentation | Rewritten README, non-technical `USER_GUIDE.md`, expanded `LIMITATIONS.md`, `CLAIMS_AUDIT_ADDENDUM.md`, completed `DEFINITION_OF_DONE.md`, `PROGRESS.md` evidence | `README.md`, `docs/` |
| Screenshots | 15 images: wizard, warnings, themes, tablet, mobile, class table, history dashboard at three widths | `docs/screenshots/01…15` |

The detection core (`spectral_pipeline.py`, `change_reasoner.py`,
`postprocess.py`, `scene_selection.py`) and the model files were **not**
modified. See §4 for the precise behavioural changes.

---

## 2. Branch and commit map

All branches are linear and fast-forwardable; no merge commits exist.

| Branch | Tip | Remote |
|---|---|---|
| `main` | `a02b27a` | `origin/main` at the same commit |
| `ui-redesign` | `fbea861` | `origin/ui-redesign` at the same commit |
| `analysis-profiles` | `44ac7e0` | `origin/analysis-profiles` at the same commit |
| `final-polish` | `af46bda` + `c571e8f` + this status commit | **local only** |

### Commits by branch (oldest → newest)

**`main..ui-redesign`** (3)
```
aba4cba Redesign UI as friendly 3-step wizard with plain-English labels
7b6beb3 Wire wizard, goal picker, theme toggle, quality badge and friendly errors in JS
fbea861 Add browser test suite and screenshots for the redesigned UI
```

**`ui-redesign..analysis-profiles`** (7)
```
cb09168 Add analysis profiles: water rules, class table, explanations, warnings
4de953d Show class table and per-region explanations in results UI
24224c5 Extend UI tests for class table and water profile wiring
5262e95 Add profile, export-parity and reference-check tests
d53cb87 Add screenshots of the results class table in dark and light themes
d967a91 Enrich PDF report with plain summary, legend, class table and credits
44ac7e0 Test PDF sections, honesty wording, missing inputs and number parity
```

**`analysis-profiles..final-polish`** (18)
```
f1720b5 Retry transient Copernicus calls and cache scene downloads in memory
6957eba Report CNN and spectral availability in /health
3f51766 Test retries, cache bounds and health availability
1ed6db5 Document Cloud Run deployment and scene-cache settings
0c1a994 Fix lint findings in report builder and report tests
45f6162 Fix composite crash when extended indices are missing
a19907b Add stored-analysis PDF endpoint and rate-limit history routes
29ca597 Raise light-theme secondary text contrast above 4.5:1
29e4499 Document the redesigned app, profiles, reports and evidence limits
96c090a Align reference raster to the AOI grid and clean new-file lint
d5e835c Omit missing AOI fields from reports instead of question marks
dffaac2 Sync docs with final suite time and lint scope
c0d6627 Add final release report
2a8c344 Add saved-analyses dashboard and compact mobile tab labels
8870e59 Test history dashboard aggregates and capture responsive screenshots
af46bda Document the history dashboard and final counts
c571e8f Correct final report commit count and run timing
(this commit) Make DoD statuses explicit and list unverified items
```

Use `git rev-parse --short final-polish` after checkout for the exact tip.

---

## 3. Test results

### Full suite, per branch

| Branch | Result | Time | How measured |
|---|---|---|---|
| `main` (baseline) | **137 passed, 3 skipped**, 1 warning | — | `pytest -q` before any changes |
| `ui-redesign` | **140 passed, 3 skipped**, 1 warning | 71.72 s | temporary worktree with the project venv linked |
| `analysis-profiles` | **179 passed, 3 skipped**, 1 warning | 72.07 s | temporary worktree with the project venv linked |
| `final-polish` | **194 passed, 3 skipped**, 1 warning | **88.41 s** on the final verification run (61.04 s post-dashboard, 42.00 s pre-dashboard) | `pytest -q` in this checkout |

That is **57 more passing tests** than the baseline. No test was deleted or
skipped to make the suite pass.

### The three skips (environment gaps, not failures)

| Test file | Reason |
|---|---|
| `tests/test_oscd_label.py` | `rasterio` is not installed (benchmark-only dependency) |
| `tests/test_finetune_cnn.py` | `torch` is not installed locally (training-only) |
| `tests/test_regression_and_api.py` | Dataset sample `dataset/test/A/test_100_0_0.png` is absent |

### The one warning

`StarletteDeprecationWarning` from FastAPI's `TestClient` about `httpx2`
(third-party, not this code).

### Changed test files (current total in each)

| File | Tests | Covers |
|---|---|---|
| `tests/test_ui.py` | 4 | wizard flow and goal sync, theme toggle and friendly network error, results dashboard and mobile layout, history dashboard and empty state (Playwright + system Chrome, port 8029) |
| `tests/test_profiles_phase2.py` | 27 | profile rules, class table, explanations, warnings, water labels |
| `tests/test_reports.py` | 6 | every PDF section, plain summary, missing inputs, number parity |
| `tests/test_live_api.py` | 24 | stored-analysis PDF endpoint, history rate limits, live-flow fakes |
| `tests/test_robustness.py` | 11 | retries, cache bounds, health, composite regression |
| `tests/test_reference_check.py` | 4 | agreement report maths and CLI guards |
| `tests/test_radiometric_compositing.py` | 8 | composite masks and broadcasting |

Python 3.10, `ruff 0.17.1`.

### Lint

- Every changed Python file is clean **except `app.py`**, which keeps **27
  pre-existing findings** (the same file on `main` has 29). They are
  intentionally not mass-fixed; 12 are auto-fixable.
- `git diff --check main...final-polish` is clean.

### Other verification performed

- PDF: first page inspected visually after the missing-AOI fix; all sections
  asserted by tests. Only the first page was inspected as an image.
- CSV / GeoJSON / PDF numbers come from the same class table and are checked
  for parity in tests.
- Browser tests run against mocked Copernicus routes; screenshots therefore
  show the interface and wiring, not a live satellite analysis.
- The Phase 4 load smoke run is recorded in `DEFINITION_OF_DONE.md`:
  120/120 analysis requests and 200/200 page requests with a fake upstream.
  It was not repeated for this report.

---

## 4. What changed, precisely

Additive:

- New route `GET /history/{analysis_id}/report` (404 for unknown IDs).
- New `/health` fields `cnn_available` and `spectral_available`.
- Response JSON gains class-table, explanation and warning fields; existing
  fields keep their meaning and the PDF, CSV and GeoJSON numbers agree.
- A new water profile and the agriculture vegetation-gain rule
  (`ndvi_gain = 0.15`, additive; the pre-existing agriculture thresholds are
  explicitly marked unchanged in `threshold_provenance`).
- Scene retries and an in-memory scene cache (no API shape change).
- A history dashboard computed in the browser from the existing `/history`
  fields; no new endpoint, database column or detection path.

Behavioural changes to note:

- `/history*` routes are now covered by the existing per-client rate limiter
  (**60 requests/minute per path by default**, `RATE_LIMIT_PER_MINUTE`; `0`
  disables it). Before, `/history` was unlimited. This was added in Phase 4 so
  a history flood cannot exhaust the server.
- When Copernicus omits the extended indices (NBR/NDMI/BSI), the window
  composite now skips them and returns `ext = None` instead of crashing. This
  changes behaviour only in a case that previously raised an exception.
- On the History tab the marketing intro is hidden so the dashboard is the
  focus; the honesty note stays visible. At widths up to 480 px the tab labels
  shorten to Compare / Upload / History, and the "Experimental" badge is hidden
  from view (the accessible name still says "experimental").

Not changed:

- The detection algorithm, thresholds and minimum mapping units of the
  pre-existing general, built-up, deforestation and roads profiles.
- The CNN model files, `best_model.pt`, `weights/model.onnx`.
- `docs/paper/` and every existing file under `benchmarks/results/`.

Evidence for the protected paths:

```bash
git diff --name-only main...final-polish -- \
  docs/paper benchmarks/results weights best_model.pt model.onnx
# (no output)
```

---

## 5. Validation status and honesty checks

No profile except built-up has labelled evaluation. The UI, PDF and docs say
so in plain words.

| Profile | Label shown to the user | Labelled evidence |
|---|---|---|
| General | unvalidated, qualitative only | none |
| Agriculture (loss/gain) | unvalidated, qualitative only | none; single-date NDVI/NDMI cannot separate harvest, irrigation or seasonality from damage |
| Deforestation | unvalidated, qualitative only | none |
| Built-up | OSCD urban benchmark only | frozen `benchmarks/results/oscd_results_v2.*`: pooled F1 **0.1176**, precision 0.2419, recall 0.0777 on the official OSCD test split (urban change only). Not re-scored in this work, and the added cues/MMU are not separately evaluated |
| Roads | unvalidated, qualitative only | none; sub-pixel at 10 m, OSM is context only |
| Water | unvalidated, qualitative only | none; NDWI is unavailable because the green band is not fetched |

- The reference check measures **agreement with a reference map**, not
  accuracy, and was **not run on a real WorldCover tile** here.
- The OSCD test split was not touched or re-run in this work.
- Wording check: no "AI-powered", "state of the art" or unqualified "accurate"
  in UI, reports, README or user guide. "validated" appears only in negations
  ("not validated") or technical metadata (`validation_status`, ID validation).
- Credentials come only from `COPERNICUS_CLIENT_ID` /
  `COPERNICUS_CLIENT_SECRET`; no `.env` file is tracked, `.env.example` has
  empty values, and logs redact secret values.
- Nothing was fabricated: the numbers in the UI and PDF come from the same
  computed result, and the evidence limits are stated in the app and reports.

---

## 6. Run locally in under 5 minutes

Dependency installation is the slow step and depends on the network and package
cache; the app start and test suite are fast. After setup:

```bash
cd "/Volumes/My Passport/Projects/Mini Project/satellite-change-detection"
python3 -m venv venv
./venv/bin/python -m pip install -r requirements-dev.txt

# Full test suite (no network, fakes only):
./venv/bin/python -m pytest -q
# -> 194 passed, 3 skipped, 1 warning in about 60–90 s

# Run the app:
cp .env.example .env    # add the two Copernicus values, or use upload mode
./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

The test run is well under 5 minutes. A cold dependency install is not; the
README says "under 5 minutes once dependencies are installed".

---

## 7. Verified vs not verified

### Verified in this checkout

- Full suite: 194 passed, 3 skipped, 1 warning, 88.41 s on the final
  verification run.
- Browser tests against mocked Copernicus routes (wizard, themes, dashboard,
  mobile layout, history analytics) and the 15 screenshots.
- History dashboard: aggregate values, range buckets, empty state, 375 px
  layout, and no console errors at 1440/768/375 px (mocked history rows).
- PDF creation, sections, plain summary, provenance, and the stored-analysis
  endpoint (text assertions plus a first-page visual check).
- Retry, cache-bound, health, rate-limit and composite-crash regression tests.
- CSV/GeoJSON/PDF number parity.
- Protected paths untouched; branches linear; no tracked credentials.
- Lint scope: changed files clean apart from pre-existing `app.py` findings.

### Not verified — do not claim these

- **Docker image build/run:** Docker is not installed on this host.
- **Cloud Run / Render deployment:** documented, not executed.
- **Live CDSE end-to-end with real credentials in this checkout:** every live
  test uses a fake Copernicus client; browser tests mock the routes.
- **Real WorldCover reference comparison:** requires `rasterio` and a reference
  tile; the script is tested but was not run on real data.
- **Labelled evaluation of general, agriculture, deforestation, roads or
  water:** none exists. They are estimates.
- **CNN inference with the real ONNX model:** the model file is not present;
  `/health` reports it unavailable and the UI falls back.
- **Formal screen-reader or zoom audit:** keyboard paths and contrast were
  checked, but no formal audit was performed.
- **PDF pages after the first:** covered by text assertions, not visual review.
- **Full-repository lint:** 27 pre-existing `app.py` findings remain.
- **Audit bugs 4 (hardcoded built-up NDVI cue not in provenance), 6 (history
  list decodes full results) and 9 (Nominatim cache):** not fixed; optional and
  documented in `DEFINITION_OF_DONE.md`.
- **OSCD test split:** intentionally not run; it stays frozen.

---

## 8. Pre-merge checks

Run these from the repository root before merging. Expected output is shown.

```bash
git status --short --branch
# ## final-polish
# ?? benchmarks/results/colab_run_summary.py
# ?? benchmarks/results/oscd_loco_thresholds.py
# (the two untracked helper scripts pre-date this work; leave them or add
#  them to .gitignore, but do not commit them blindly)

./venv/bin/python -m pytest -q
# 194 passed, 3 skipped, 1 warning in about 60 s

git diff --name-only main...final-polish -- \
  docs/paper benchmarks/results weights best_model.pt model.onnx
# (no output)

git merge-base --is-ancestor ui-redesign analysis-profiles && \
git merge-base --is-ancestor analysis-profiles final-polish && \
echo "linear chain OK"
```

All three branch relationships above were verified with
`git merge-base --is-ancestor`; each merge below is a fast-forward.

---

## 9. Merge order and push commands

Do **not** merge `oscd-finetune`. The order is fixed because each branch was cut
from the previous one after its checks passed:

```bash
git checkout main
git merge --ff-only ui-redesign
git merge --ff-only analysis-profiles
git merge --ff-only final-polish

# after the merge and a final `pytest -q`:
git push origin main
```

`git push -u origin final-polish` was attempted earlier at the owner's request
and was **blocked by the permission system**; it was not retried. To publish
the branch, run it yourself:

```bash
git push -u origin final-polish
```

If you only merge into `main`, the branch push is optional.

---

## 10. Definition of Done

`DEFINITION_OF_DONE.md` marks every item Done, Partly done or Not done with
evidence; three items are partly done and the not-done list is explicit. Those
caveats are part of the record.

| Phase | Status | Evidence anchor |
|---|---|---|
| 0 — Audit | Complete | `docs/PROJECT_AUDIT.md`, `docs/DEFINITION_OF_DONE.md` |
| 1 — UI redesign | Complete | `ui-redesign` tip `fbea861`, 140 passed / 3 skipped, screenshots 01–10 |
| 2 — Analysis profiles | Done, with one partly-done item | `analysis-profiles` tip `44ac7e0`, 179 passed / 3 skipped, screenshots 11–12; WorldCover check script not run on a real tile |
| 3 — Reports and exports | Complete | `reports.py`, `tests/test_reports.py`, `/history/{id}/report` |
| 4 — Robustness | Done, with two partly-done items | retries, cache, `/health`, rate limits, composite fix, 194-test suite; Docker build unverified, full-repo lint not clean |
| 5 — Docs and honesty | Complete | README, USER_GUIDE, LIMITATIONS, CLAIMS_AUDIT_ADDENDUM, PROGRESS, this report |

Global rules: no push of `final-polish`; protected paths untouched; no
detection-math or threshold changes to existing profiles (the additive
agriculture gain rule and new water profile are called out in §4); credentials
from env only; existing tests pass and every new feature has tests; unverified
work is listed in §7 rather than claimed.

---

## 11. Sensible follow-ups (not blockers)

1. Run the app once with real credentials and compare one result against the
   screenshot flow; record it as the first live acceptance test.
2. Build the Docker image in CI (it is unbuilt here) and deploy once.
3. Score the agriculture, deforestation, water and roads profiles on labelled
   data before describing them as anything more than estimates.
4. Run `benchmarks/reference_checks/worldcover_agreement.py` on a real
   WorldCover tile; keep calling the output "agreement", not accuracy.
5. Fix or explicitly waive the 27 pre-existing `app.py` lint findings and audit
   bugs 4, 6 and 9.
6. Have someone who uses a screen reader walk the wizard and results page.
