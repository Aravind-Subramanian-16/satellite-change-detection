# Project progress

Status legend: `[x]` verified with evidence below it, `[ ]` not verified.
Evidence must be a command output or a committed file path. No benchmark number
appears here without a local result file behind it.

Checkout state (2026-10-21): `model.onnx`, `best_model.pt`, the OSCD imagery and
the learned joblib are **absent from this local checkout**. The ONNX file present
during the owner's earlier Phase A run measured 60,534,573 bytes and failed
protobuf loading; it is not the verified 33,268,410-byte Drive copy. The v2
benchmark result files are now present. The training-only LOCO result, the Colab
model check and `benchmarks/results/COLAB_RUN_SUMMARY.md` are also present.

## Phase A — Finish setup and verify

- [x] A1. Record the local `model.onnx` byte size and SHA-256; do not modify it;
  tell the owner to replace it with the Drive copy of 33,268,410 bytes.
  - Evidence (owner's earlier environment): `stat -f 'size_bytes=%z' model.onnx
    && shasum -a 256 model.onnx` → `60534573`; SHA-256
    `b3d95e3e796b3bda4b06dc37a4909a47be8b6c13460b59fed3d6f4a66e2ececd`.
    That file was invalid; replacement is still required. The file is absent
    from the current checkout, so `/model-status` reports `present: false`. The
    Colab model check (2026-10-21) confirms the Drive copy is 33,268,410 bytes,
    SHA-256 `41c2ab64...`, loads in onnxruntime and has inputs `input_a`,
    `input_b`; local app inference remains unverified.
- [x] A1b. Model-dependent features fail with a clear error instead of crashing.
  - Evidence: `tests/test_model_status.py`, `tests/test_model_load_errors.py`;
    live `POST /predict` → HTTP 503 with actionable size/Drive instructions.
- [x] A2. Install dependencies in a venv with `python -m pip`; run
  `python -m pytest -q`; record exact counts.
  - Evidence: split runtime/benchmark/dev requirements; local install succeeded
    (fastapi 0.156.3, numpy 2.2.6, onnxruntime 1.19.2, scikit-learn 1.7.2).
    `./venv/bin/python -m pytest -q` → **113 passed, 3 skipped, 1 warning in
    14.64s** (runtime varies) after the Phase F figure tests (Phase E: 108
    passed, 3 skipped,
    11.09s; Phase D2: 96 passed, 3 skipped, 10.82s; Phase D: 72 passed, 2
    skipped, 7.87s; Phase B/C: 60 passed, 2 skipped, 3.87s; initial Phase A:
    41 passed, 2 skipped, 4.64s). Skips: the
    Pipeline A regression (needs `model.onnx` and a dataset sample), OSCD label
    tests (rasterio is benchmark-only on this host) and the torch-only
    crop-dataset smoke test.
    Details: `docs/PHASE_A_REPORT.md#a2-dependencies-and-tests`.
- [x] A3. Start the app and verify `/health`, upload flow, dashboard, slider,
  heatmap, report download and History; save screenshots; record console errors;
  mark anything not run unverified.
  - Evidence: `docs/PHASE_A_REPORT.md#a3-browser-verification`;
    `docs/screenshots/phase_a_*.png`;
    `docs/screenshots/phase_a_report_sample.pdf` (168,765 bytes, downloaded via
    the UI). Dashboard/slider/heatmap used a **synthetic injected result**;
    real CNN inference is unverified without weights. Console: expected 503
    from `/predict`, one missing-favicon 404, no page errors.
- [x] A4. Build Docker if available and check `/health` plus PDF generation;
  otherwise state Docker is unavailable.
  - Evidence: `docker --version` → command not found. Image checks are
    **unverified**; recorded in `docs/PHASE_A_REPORT.md#a4-docker`.
- [x] A5. Add `.env.example` (no secrets), `render.yaml` (free tier, CPU only,
  health check) and `DEPLOY.md`.
  - Evidence: `.env.example`, `render.yaml` (`plan: free`, Docker, `/health`,
    no GPU), `DEPLOY.md`.

## Phase B — Live map picker with best-image selection

Verified 2026-10-21. The UI screenshots `docs/screenshots/phase_b_live.png`,
`phase_b_scenes.png`, `phase_b_results.png` and `phase_b_mobile.png` were
captured with Playwright route interception and **mocked API responses**. Each
image carries a visible “MOCKED API RESPONSES / MOCKED DATA” banner. They prove
UI wiring only, not a real Copernicus analysis. Browser console contained only
the intentional mocked `/predict` 503; there were no page errors; mobile
horizontal overflow was 0 px and all three tabs rendered at 37 px height.

- [x] B1. Leaflet pinned to an exact cdnjs version with OSM tiles (optional Esri
  World Imagery), correct attribution, no API keys; place search/geocoding,
  zoom-to-location, AOI box; minimum zoom ~12 before confirmation; maximum AOI
  10 km × 10 km configurable; AOI area in km² and expected pixel dimensions;
  clear too-large / too-zoomed-out messages.
  - Evidence: `static/index.html:8-12` pins Leaflet 1.9.4 and Leaflet.draw
    1.0.4; `static/app.js` uses OSM tiles with attribution, Nominatim search
    and `fitBounds` zoom-to-place; “Use current view” is refused below zoom 12
    (verified by the Playwright smoke test); drawn boxes auto-fit to at most
    zoom 14 before applying. `computeAoi()` reads `max_aoi_km` from `/config`
    (default 10) and reports width/height/area/raster plus per-side errors.
    Manual box `55.10,25.00,55.12,25.02` was accepted as 4.49 km².
- [x] B2. Before/after date pickers with a ± window (default 30 days).
  - Evidence: `#date-before`, `#date-after`, `#window-days`; default window
    from `live_pipeline.DEFAULT_WINDOW_DAYS`; UI validates ISO dates and order.
- [x] B3. `/scenes` queries the Copernicus catalog for Sentinel-2 L2A scenes
  intersecting the AOI per window; ranks by AOI coverage, cloud cover and
  closeness to requested date; returns top 5 per window with date, cloud % and
  coverage %; UI shows a “recommended” badge and allows override; warns when the
  two dates fall in different seasons.
  - Evidence: `app.py:_catalog_windows`, `scene_selection.rank_scenes`;
    `tests/test_scene_selection.py` and
    `tests/test_live_api.py::test_scenes_returns_ranked_windows_and_recommendation`,
    `::test_scenes_warns_on_partial_coverage_and_cross_season`.
    `docs/screenshots/phase_b_scenes.png` shows rank/recommended badges and the
    season + coverage warnings.
- [x] B4. After fetching, compute cloud and shadow fraction over the AOI from
  SCL; above a configurable 30% warn and suggest the next-best scene; fully
  masked uses the existing error state.
  - Evidence: `live_pipeline.cloud_fraction` and `_fetch_window`;
    `CLOUD_WARN_PERCENT` default 30; next-best suggestions in the warning;
    `FullyMaskedError` → HTTP 422 with window, fraction and candidates.
    Tests: `::test_fetch_and_predict_honours_selected_scene_and_warns_on_cloud`,
    `::test_fetch_and_predict_returns_422_details_when_scene_is_fully_masked`.
- [x] B5. Pass AOI and chosen scenes through the existing pipeline without
  changing detection logic in this phase.
  - Evidence: `analyse_pair` resolves `scene_before_id` / `scene_after_id` in
    `choose_scene_window` and calls the existing `detect_profile`; API tests
    assert the selected IDs reach the result.
- [x] B6. UI shows pipeline used, percent masked, scene IDs and dates, and a
  decision-support-not-ground-truth note.
  - Evidence: results header, stat grid, summary and provenance in
    `docs/screenshots/phase_b_results.png`; Playwright assertions for
    `#result-stats`, `#result-summary` and `#provenance`.
- [x] B7. pytest tests with mocked catalog responses covering ranking, AOI
  limits, season warning and cloud warning.
  - Evidence: `tests/test_live_api.py` (18 cases, network-free fake client)
    plus `tests/test_scene_selection.py`; full suite 60 passed, 2 skipped.

## Phase C — Analysis profiles

Verified 2026-10-21 from code, synthetic-array tests and the mocked UI run.
No accuracy number is displayed for any unvalidated profile.

- [x] C0. Add an analysis-profile selector to UI and API; each profile is a
  small declarative config (indices, thresholds, MMU, report wording, honesty
  notes) on top of `spectral_pipeline.py` and `change_reasoner.py`; general
  profile remains default and unchanged.
  - Evidence: `profiles/__init__.py` registry, `profiles/detection.py`,
    `#profile-select`; `tests/test_profiles.py::test_registry_never_hides_unvalidated_status`.
- [x] C1. Agriculture: NDVI and NDMI difference, cropland stress /
  vegetation-loss flags, enforced same-season warning, optional 3–5 date NDVI
  timeline; report wording explains that single-pair differences confuse
  harvest/season cycles with damage.
  - Evidence: `test_agriculture_flags_stress_and_vegetation_loss`;
    `POST /timeline` tests in `tests/test_live_api.py`; timeline is rendered in
    `phase_b_results.png`; profile notes state the season/harvest caveat.
- [x] C2. Deforestation: NBR and NDVI drop restricted to pixels vegetated in the
  before image, configurable MMU (default 0.5 ha), area in hectares per region,
  mandatory cloud/shadow masking.
  - Evidence: `test_deforestation_requires_vegetated_before_and_mmu`,
    `test_deforestation_mmu_removes_small_patch`,
    `test_cloud_shadow_is_masked_mandatorily`; regions receive `area_ha` in
    `live_pipeline._enrich_regions`.
- [x] C3. Built-up/industrial: NDBI, built-up index and bare-soil index change
  with an NDVI-loss cue; existing change reasoner distinguishes new construction
  from cleared land.
  - Evidence: `test_builtup_ndbi_and_bare_soil_cues`; API test
    `test_fetch_and_predict_supports_builtup_extended_indices` exercises the
    `indices_ext` BSI/NDMI/NBR layer.
- [x] C4. Roads: UI/docs state that roads narrower than ~20 m are mostly
  sub-pixel at 10 m; do not claim road detection; optional cached OSM/Overpass
  road overlay with attribution and ODbL caveat; report “changed area within X m
  of mapped roads” as context only.
  - Evidence: roads profile wording and `show_road_context`;
    `osm_roads.py` (cached Overpass query, ODbL attribution);
    `tests/test_exports_and_osm.py::test_road_context_reports_only_nearby_changed_pixels`;
    results screenshot shows the context box and “not road detection”.
- [x] C5. Validation-status badge from `profiles/validation_status.json`:
  built-up “quantitatively benchmarked on OSCD (urban change only, pooled F1
  about 0.12)”; all others “unvalidated, qualitative only”; never show accuracy
  numbers for unvalidated profiles.
  - Evidence: `test_registry_never_hides_unvalidated_status`; API assertions on
    `display_metrics`; Playwright asserts the unvalidated banner contains no
    “F1”. Built-up evidence points to `benchmarks/results/oscd_results_v2.json`
    and `.md` (F1 0.1176).
- [x] C6. PDF reports include profile, thresholds, MMU, scene IDs, dates,
  percent masked, code commit hash, validation status and limitations; add
  GeoJSON and CSV exports of regions with area, type and confidence.
  - Evidence: `reports.py`; new
    `tests/test_reports.py::test_pdf_report_contains_method_provenance_and_unvalidated_badge`
    decodes the PDF content stream and checks those fields;
    `tests/test_live_api.py::test_export_and_report_endpoints`; mocked UI
    download produced a 9,157-byte PDF.
- [x] C7. pytest tests on synthetic arrays for each profile (index math, MMU,
  vegetated-before restriction, season warning).
  - Evidence: `tests/test_profiles.py` (11 tests across agriculture,
    deforestation, built-up, roads, index math, MMU, cleanup); season-warning
    tests in `tests/test_scene_selection.py` and `tests/test_live_api.py`.

## Phase D — Learned model beyond the CNN (OSCD train only)

Verified 2026-10-21 from code and synthetic-array tests. The local checkout has
no OSCD imagery and no joblib artifact, so **training, held-out validation
numbers and real-artifact inference are unverified**. No learned accuracy
number is claimed.

- [x] D1. `benchmarks/train_pixel_classifier.py`: gradient-boosted trees or
  random forest (scikit-learn, CPU) on per-pixel band reflectances for both
  dates, NDVI/NDBI/NBR/NDMI/BSI differences, and 3×3/7×7 local means; train on
  14 OSCD TRAIN cities with 3 fixed seeded held-out train cities; never read the
  10 test cities during training/selection.
  - Evidence: `learned_features.py` builds a 55-feature stack (12 bands, 10
    indices, 11 differences, 22 local means);
    `benchmarks/train_pixel_classifier.py` requires exactly 14 train cities,
    seeds the 3 held-out cities (`DEFAULT_SEED=42`), fits on 11, selects the
    threshold on held-out TRAIN only, and records
    `official_test_cities_excluded` + `test_split_scored: false`. The trainer
    raises through `assert_no_test_cities` before reading rasters. Training has
    **not** been run locally; `notebooks/oscd_pixel_classifier.ipynb` is the
    owner-run Colab path.
- [x] D2. Save the model as a small joblib file outside git; loader available to
  the app as an optional “learned” pipeline behind a flag; explainable spectral
  pipeline stays default.
  - Evidence: `*.joblib` and `artifacts/` are in `.gitignore`;
    `learned_pipeline.py` loads a dict bundle lazily and validates feature
    layout and threshold. `POST /predict-learned` requires
    `ENABLE_LEARNED_MODEL=1` (otherwise HTTP 503
    `learned_pipeline_disabled`), accepts two six-band `.npz` uploads, returns
    `display_metrics: false`, experimental validation text and provenance, and
    never changes the default spectral/live path. `GET /learned-model-status`
    reports enabled/present/loaded. Documented in README and `.env.example`.
    Synthetic fake-model test:
    `tests/test_learned_pipeline.py::test_learned_status_and_endpoints`.
- [x] D3. `notebooks/oscd_pixel_classifier.ipynb` matching `oscd_benchmark.ipynb`
  setup; not run locally; results unverified until owner pastes Colab output.
  - Evidence: notebook mounts Drive, unzips the same OSCD archive, pulls/clones
    the repo, installs benchmark requirements, runs the learned tests, verifies
    14 TRAIN cities + labels, runs the trainer to a Drive artifact, and prints
    the artifact's held-out TRAIN metadata. It does not unzip/use test labels or
    score test cities. **Not executed locally; no output pasted.**
- [x] D4. Tests with synthetic data for the feature builder and the no-test-city
  guard.
  - Evidence: `tests/test_learned_features.py` (6 tests: shapes/names/index
    math, local means, both window sizes, determinism, missing-band/shape
    errors, test-city guard) and `tests/test_learned_pipeline.py` (6 tests:
    fake-model prediction, threshold override, feature-layout mismatch, missing
    model, npz validation, endpoint status/disabled/503/400/success). Full suite
    after Phase D2: 96 passed, 3 skipped.
- [x] D5. Test-set scoring deferred to Phase D2 step 6 for pre-registered
  systems only.
  - Evidence: trainer never scores a test city and writes
    `test_split_scored: false`; no v3 result file exists; README and notebook
    state the deferral. Phase D2.6 remains blocked locally without OSCD data
    and weights.

## Phase D2 — X-factors and autonomous accuracy improvement

- [x] D2.1. `docs/paper/XFACTORS.md`: differentiators, evidence needed, prior-work
  comparison topics as `[CITE: topic]`, status implemented/partial/idea.
  - Evidence: `docs/paper/XFACTORS.md` lists eight candidates with status,
    local evidence, missing evidence and citation topics; it makes no priority
    or superiority claim.
- [x] D2.2. Implement behind flags, each with a synthetic-data test, default
  pipeline unchanged: (a) radiometric normalisation, (b) temporal median
  compositing, (c) morphological cleanup + object MMU, (d) CNN fine-tuning on
  OSCD train only (new file, never `best_model.pt`), (e) fusion/stacking, (f)
  uncertainty from model agreement with ECE on held-out train cities.
  - Evidence:
    (a) `radiometric.py`, `tests/test_radiometric_compositing.py` (affine
    recovery, no-op, clipping, profile-level false-positive removal); UI flag
    `normalise` is off by default.
    (b) `compositing.py`, same test file (median excludes masks, all-masked
    → NaN, clear fraction); API option `composite_scenes` is 1–3, default 1.
    (c) `postprocess.py`, `tests/test_profiles.py` (MMU, cleanup no-op) and
    `tests/test_radiometric_compositing.py`; API flag `cleanup` default false.
    (d) `benchmarks/finetune_cnn.py` writes a new checkpoint, guards
    `best_model.pt`/`model.onnx`, uses 3 held-out TRAIN cities and logs
    `test_split_read: false`; `tests/test_finetune_cnn.py` covers guards,
    crops, threshold sweep, and a torch-only dataset test (**skipped locally**).
    Actual fine-tuning is unverified.
    (e) `fusion.py`, `tests/test_fusion.py` (complementary-signal recovery,
    weight/threshold selection); not wired into the default app.
    (f) `uncertainty.py`, `tests/test_uncertainty.py` (ECE, overconfidence,
    agreement, held-out-TRAIN guard). Real calibration is unverified.
    Default spectral/live behaviour is unchanged; full suite 96 passed,
    3 skipped.
- [x] D2.3. `benchmarks/auto_improve.py`: fixed search space/seeds,
  leave-city-out CV over 14 train cities, hard trial budget, every trial logged
  to `benchmarks/results/auto_improve_log.json` including failures, selection by
  validation F1 only, guard that raises if any test city is read, ablation tables
  on validation only.
  - Evidence: 12 fixed systems, `HARD_TRIAL_BUDGET=12`, 14 leave-one-city-out
    folds, threshold grids refit on the 13 fit cities, `assert_no_test_cities`
    before any load, JSON checkpoint after every trial, markdown tables with
    mean±SD per-city F1 and paired component deltas. Tests:
    `tests/test_auto_improve.py` (guard, hard budget, failure logging,
    checkpointed output, validation-only metadata). **No log exists yet**;
    owner must run the notebook.
- [x] D2.4. `notebooks/oscd_auto_improve.ipynb` (Colab); not run locally; gains
  unverified until owner pastes output.
  - Evidence: notebook exists; mounts Drive, verifies 14 TRAIN cities, runs the
    12-trial search into `benchmarks/results/auto_improve_log.json`, copies it
    to Drive, asserts 12 trials and `test_split_read: false`, and leaves CNN
    fine-tuning off by default. **No output pasted; not executed locally.**
- [x] D2.5. `docs/paper/PREREGISTRATION.md` committed before any test scoring,
  listing exact systems, metrics and selection rule.
  - Evidence: committed protocol dated 2026-10-21 (this commit precedes any v3
    file); exact S0–S3 definitions, fixed metrics, training-only selection rule,
    one-event protocol, deviation rules and no-post-test-tuning clause.
- [ ] D2.6. Score the 10 test cities ONCE for pre-registered systems into
  `oscd_results_v3.json/.md` without overwriting v2; record the third scoring; no
  tuning/reselection after seeing results. **Blocked: OSCD data and weights
  absent locally; only Colab can run it.**
- [x] D2.7. Report improvements with variance across cities; drop and log
  components that do not help on validation.
  - Evidence: `auto_improve.py` records pooled and per-city F1, mean±SD,
    min/max, paired component deltas, a `kept`/`dropped` decision per component,
    and a recommendation that excludes dropped components. This is implemented
    and synthetic-tested only; **no real validation result exists yet**.

## Phase E — Production hardening

- [x] E1. Upload validation (type, size, dimensions), rate limiting, strict
  CORS, security headers, no secrets in logs, structured logging, request IDs,
  non-root Docker user, pinned compatible dependency ranges that install on
  Colab (no onnx pin; onnx only in `requirements-dev.txt`).
  - Evidence: `security.py` + 12 tests in `tests/test_security.py` cover
    extension/content-type/byte/dimension rejection (400/413/415), `.npz`
    declared-size and pixel caps, per-IP/per-path sliding-window 429 with
    `Retry-After`, same-origin-by-default CORS (`ALLOWED_ORIGINS`, `*` ignored),
    CSP/nosniff/frame/referrer/permissions headers, validated or generated
    `X-Request-ID` echoed on responses and errors, JSON access logs and
    credential redaction. `Dockerfile` already ran as UID 10001; it now also
    runs uvicorn with `--no-access-log` because the app emits structured access
    logs. Dependency ranges were already compatible with Colab and keep ONNX
    out of the runtime pin. **Docker build remains unverified (Docker absent).**
- [x] E2. GitHub Actions workflow running pytest on push with model-dependent
  tests skipped cleanly.
  - Evidence: `.github/workflows/tests.yml` runs `python -m pytest -q` on
    Python 3.10 for push/PR with a 20-minute timeout and failure artifact; the
    three model/data-dependent skips are enforced by the tests themselves and
    reproduced locally. **The workflow has not run on GitHub because every push
    failed with HTTP 400; remote CI remains unverified.**
- [x] E3. Accessibility/UX review: keyboard slider, colour-blind-safe heatmap,
  legends/units, loading and error states for every failure, responsive layout,
  empty states.
  - Evidence: the before/after control is a native range input with a visible
    label and percentage; the heatmap now uses a viridis palette with monotonic
    luminance, matching CSS swatch, canvas `role="img"`/label and a text legend
    that states it is not a probability. Tabs, segmented controls, sliders and
    AOI inputs have keyboard handlers and `aria-selected`/`aria-live`/`role`
    annotations; loading uses a labelled busy overlay, and history, search,
    scenes, regions and errors have explicit empty/loading/error text. A live
    browser check loaded Leaflet and six OSM tiles under the new CSP with no
    console messages; Phase B's mocked responsive check recorded 0 px
    horizontal overflow on mobile. A formal screen-reader and zoom audit was
    **not** performed.
- [x] E4. Provenance on every result: commit hash, pipeline, profile,
  thresholds, scene IDs, dates, percent masked, timestamp.
  - Evidence: `provenance.py` emits commit, app version, pipeline, profile,
    thresholds, scene IDs, dates, percent masked and UTC timestamp; live,
    learned, CNN and exported/report paths attach or render it, with tests in
    `tests/test_provenance.py`, `tests/test_live_api.py`,
    `tests/test_exports_and_osm.py` and `tests/test_reports.py`. Optional
    compositing/normalisation/MMU settings are included in live provenance.
- [x] E5. `docs/LIMITATIONS.md`: 10 m resolution, seasonal confusion, clouds,
  no ground-truth guarantee.
  - Evidence: `docs/LIMITATIONS.md` covers resolution/mixed pixels, per-profile
    validation status and v2 numbers, spectral confusion, clouds/shadow,
    temporal/geometric limits, MMU/compositing/PIF, the experimental learned
    model, OSM/licensing, missing authentication/history privacy, rate-limiter
    scope and the evidence needed before operational use.

## Phase F — Paper and presentation

- [x] F1. `docs/paper/paper.tex` (IEEEtran) with abstract, introduction,
  related work placeholders, methods, experiments, results tables generated from
  JSON, ablations, discussion, limitations, conclusion.
  - Evidence: this Phase F draft was superseded by the Step 3 manuscript
    below. It was **not compiled**: no `pdflatex`/`tectonic`/`latexmk` on this
    host.
- [x] F2. Honest framing (negative transfer: aggregate CNN F1 0.0007; spectral
  percentile F1 0.1176, hardcoded 0.0782, Otsu F1 0.0953 with OA 0.3439 as its
  headline; prior test scoring disclosed, total event count not recorded; v3
  uncomputed; four non-built-up profiles unvalidated).
  - Evidence: abstract and results in `paper.tex`; v2 JSON/MD; the four
    unvalidated profiles are `general`, `agriculture`, `deforestation` and
    `roads` (plus experimental learned/fusion paths). `CLAIMS_AUDIT.md` lists
    30 claims and the not-claimed list. No unvalidated accuracy number is
    displayed.
- [x] F3. `[CITE: topic]` placeholders and `docs/paper/TODO_CITATIONS.md`; no
  invented references or baselines.
  - Evidence: 18 citation slots covering OSCD, LEVIR-CD, Sentinel-2,
    indices, Otsu, PIF, surveys, calibration, reproducibility, licences,
    cross-sensor transfer, test-set reuse, preregistration, spatial CV and
    open tools. All statuses unverified; no DOI/author/year was invented.
- [x] F4. `scripts/make_paper_figures.py` reading saved JSON and writing
  `docs/paper/figures/` (per-city F1, predicted vs true fraction,
  precision–recall, ablation, reliability, qualitative placeholder); test with
  fake JSON.
  - Evidence: superseded by Step 3, where the generator was rewritten to write
    two figures and two tables from the saved OSCD JSON and degradation CSV.
    The Phase F version wrote six PNGs and three `.tex` tables and validated
    10 cities × 5 methods.
- [x] F5. `CLAIMS_AUDIT.md`, `THREATS_TO_VALIDITY.md`, `REPRODUCIBILITY.md`
  (commands, hashes, seeds, Colab steps, OSCD CC BY-NC-SA and commercial-use
  caveat).
  - Evidence: all three files are present, plus `FUTURE_WORK.md`. They record
    the v2 source hash, code commit `a6dad9e`, seeds, commands, environment,
    skips and the unverified items (Docker, CI, LaTeX, Colab, v3, weights).
    Licence terms are marked as requiring external verification/legal review.
- [x] F6. `NOVELTY_CHECKLIST.md` with 3–5 searches per claimed contribution,
  databases, status unverified.
  - Evidence: `docs/paper/NOVELTY_CHECKLIST.md` records 15 Qoder WebSearch
    queries (5 per contribution) with dates, selected titles/URLs, the
    databases **not** searched, and “unverified” verdicts. Its overall status
    is unverified and no priority claim is permitted.
- [x] F7. `VENUES.md` with venue types and expectations; scope/length/fees
  flagged for verification; no impact factors or acceptance rates.
  - Evidence: `docs/paper/VENUES.md` covers software venues, conferences,
    journals, workshops and preprints; every scope/length/fee item is marked
    for verification; it explicitly contains no impact factors or acceptance
    rates and recommends a workshop/software venue over a methods journal in
    the current state.
- [x] F8. `SUBMISSION_CHECKLIST.md`: anonymisation, data/code availability,
  licences, ethics/dual-use, contributions, arXiv decision, AI-assistance
  disclosure.
  - Evidence: `docs/paper/SUBMISSION_CHECKLIST.md` has sections A–L with
    blocking items: no verified citations/bibliography, no code `LICENSE`, no
    compiled PDF, no v3/independent validation, blank authors/contributions,
    unresolved anonymisation, incomplete novelty search. Readiness: **not
    ready**.
- [x] F9. `docs/presentation/slides.md` (12 slides, speaker notes, live-demo
  script) and `docs/presentation/QA.md` (20 honest reviewer questions).
  - Evidence: `docs/presentation/slides.md` has exactly 12 slides with speaker
    notes, three demo paths (mocked UI, local UI, report/export), failure
    scripts, timing and a “do not say” list. `docs/presentation/QA.md` has 20
    questions with answers limited to v2 evidence and explicit unverified
    items.
- [x] F10. Future work: human-feedback loop, labelled agriculture/deforestation
  data, higher-resolution roads, unfinished D2 ideas.
  - Evidence: `paper.tex` Discussion `Future Work` subsection and
    `docs/paper/FUTURE_WORK.md` (P0/P1/P2 items, dependencies, evidence needed,
    explicitly not planned actions). These are plans, not results.

## Phase commit and push log

- Phase A checkpoint: rebased onto remote v2 results; commit hash recorded in
  `git log` (message begins “feat: harden model fallback”). Push attempted.
- Phase B/C commit: `dc5009b` (live map workflow, profiles, reports). Push
  attempted with `git push origin main`; failed with
  `RPC failed; HTTP 400 curl 22` and the remote still reported “Everything
  up-to-date”. No force push.
- Phase D commit: `376325f` (optional learned pixel classifier). Same push
  failure; local branch then ahead of `origin/main`.
- Phase D2 commit: `0d7082d` (validation-only search, fusion, uncertainty,
  fine-tuning, preregistration). Same push failure. At the time of writing,
  `main...origin/main [ahead 5]`; v3 is not run locally.
- Phase E commit: `a6dad9e` (uploads, rate limits, headers, logging, viridis
  heatmap, limitations). Push not retried after the repeated HTTP 400; local
  branch ahead by six commits. Remote CI remains unverified.
- Phase F commit: `7faba84` (paper, generated figures/tables, claims/threats/
  reproducibility/novelty audits, venue and submission checklists, 12-slide
  deck, 20-question Q&A, future work). The automated push attempt was blocked
  before execution because of the prior repeated HTTP 400; **nothing was
  pushed**. Local `main` is ahead of `origin/main` by seven commits. Remote CI
  and the GitHub Actions workflow remain unverified. Run the push manually from
  the owner terminal (no force):
  `git push origin main`.
- Push success (2026-10-21): the owner fixed the HTTP 400 by switching the git
  client to HTTP/1.1. The push reported `40c4c15..e8b6678 main -> main`, so all
  35 prior commits are on the remote. The Step 7b documentation commit remains
  local until the owner pushes it; no force push or history rewrite was used.

## Submission task (2026-10-21)

New ordered scope: correct the existing draft, add saved-data evidence, build an
IEEEtran paper, prepare reviewer materials, a talk, verify the app, and hand off
a one-click Colab notebook. No test re-scoring, no v3, no training.

- [x] Step 0. Push diagnosis and repository size audit.
  - Evidence: `docs/REPO_PUSH_DIAGNOSIS.md`; `git rev-list --objects --all`
    blob scan returned no blob >20 MB; `.git` 8.7 MB; largest blob 1.74 MB;
    preventive `.gitignore` entries added. Commits `8989525`, `e068b23`.
    `git push origin main` still fails with HTTP 400 on a small commit, so
    large files are not the cause. No history rewrite performed.
- [x] Step 1. Correct the existing draft on a copy.
  - Evidence: `docs/paper/DRAFT_CORRECTION_LOG.md` and
    `docs/paper/paper_draft_revised.docx`. Original left untouched at
    `/Users/aravind/Downloads/IEEE_Paper_Draft_Resolution_Mismatch_Change_Detection.docx`
    (SHA-256 `69442ffb...`). Table I recomputed from
    `degradation_results.csv`; Table II corrected to 924+4+5+2=935 (revision
    note in `DRAFT_CORRECTION_LOG.md`; commit `f317d89`);
    “stable between 0.5 and 1 m” and “precision above 97%” fixed; exact
    blur/LANCZOS method and AdamW/27-epoch training details corrected; OSCD
    v2 results added; repeated test scoring disclosed; no one-shot claim;
    overclaims and unverified numbers removed or hedged. Commit `52c2130`.
- [x] Step 2. Source-backed OSCD evidence: trivial baselines, city bootstrap
  CIs (seed 0, 10,000), paired bootstrap, failure/correlation analysis,
  CNN input and blur specifications, train-only LOCO script with a synthetic
  test; LOCO result produced on Colab from training cities only.
  - Evidence: `benchmarks/oscd_evidence.py` reads only
    `benchmarks/results/oscd_results_v2.json` (SHA-256 `37ffe2bb...`, unchanged)
    and writes `benchmarks/results/oscd_evidence.json` plus `.md`. It adds
    all-no-change and random-at-prevalence baselines, a seed-0/10,000-resample
    city bootstrap with percentile intervals and paired differences against the
    hardcoded rule, per-city predicted/true fractions, correlations, and the
    exact band/scaling/tiling/degradation specification. No imagery or test
    labels are read. `tests/test_oscd_evidence.py` checks validation, baselines,
    bootstrap pairing, failure flags, and the saved v2 values.
  - Evidence: `benchmarks/oscd_loco_thresholds.py` selects hardcoded and
    percentile thresholds on 13 training cities and scores the held-out
    training city using the same grids as `benchmarks/oscd_eval.py`; it rejects
    official test cities in `train.txt` and accepts no test-label path.
    `tests/test_oscd_loco.py` covers the selection/exclusion logic, tie order,
    guards, and report assembly with synthetic index arrays. The real result is
    `benchmarks/results/oscd_loco_thresholds.json` (SHA-256 `32d1dbf5...`):
    14 training cities, hardcoded pooled held-out F1 0.0976 (IoU 0.0513,
    precision 0.0838, recall 0.1168), percentile F1 0.1469 (IoU 0.0793,
    precision 0.1544, recall 0.1401); hardcoded grid-edge in 14/14 folds,
    percentile 0/14; no official test city in `train.txt` and no test-label path
    accepted. It is a training-split robustness check, not a test score.
  - Tests: `126 passed, 3 skipped, 1 warning in 20.78s`
    (`venv/bin/python -m pytest -q`, 2026-10-21). Commits `b819f53`,
    `6454b87`. The `.gitignore` root-results pattern was narrowed so
    `benchmarks/results/` evidence stays trackable. Push remains blocked by the
    environment after the earlier HTTP 400 failures; no force push or history
    rewrite was attempted.
- [x] Step 3. IEEEtran paper within four pages excluding references, with
  `[CITE: topic]` placeholders only and figures generated from saved JSON.
  - Evidence: `docs/paper/paper.tex` is a new IEEEtran conference manuscript
    (title: “Resolution-Induced Performance Collapse of a CNN Change Detector:
    Simulated and Real Sentinel-2 Evidence”) with a one-paragraph system
    overview, the controlled degradation experiment, the OSCD evaluation,
    discussion, limitations, conclusion and 15 `[CITE: ...]` slots; there is no
    bibliography and no asserted reference metadata. About 2,609 source words
    by `python` count with commands stripped; four floats (two figures, two
    generated tables).
  - Assets: `scripts/make_paper_figures.py` reads only
    `benchmarks/results/oscd_results_v2.json` (SHA-256 `37ffe2bb...`) and
    `degradation_results.csv`; it wrote
    `fig_f1_vs_resolution.png`, `fig_oscd_per_city_and_fractions.png`,
    `generated_degradation_table.tex`, `generated_oscd_table.tex` and
    `figure_manifest.json` (commit `730b025`). The OSCD table includes OA so
    Otsu's headline score is visible.
  - Number cross-check: recomputing from `degradation_results.csv` gives, at
    10 m, 2,048 images, 935 changed, 91,006 predicted pixels, 6,837,404
    changed ground-truth pixels, TP 90,527, FP 479, and 924/4/5/2 images with
    no prediction / IoU < 0.1 / 0.1–0.5 / ≥ 0.5. Pooled F1 values are 87.06,
    70.81, 4.41, 2.84, 2.61 and 2.61 from factors 1–20. OSCD values match
    `benchmarks/results/oscd_evidence.json`.
  - Static checks: braces balanced (77/77 with `\input` expanded); all labels
    resolve (`tab:degradation`, `tab:oscd`, `fig:resolution`, `fig:oscd`); all
    four assets exist; no occurrence of “first”, “novel”, “state of the art”,
    “one-shot”, “resolution-agnostic” or “under-studied”.
  - Tests: `128 passed, 3 skipped, 1 warning in 10.35s`
    (`./venv/bin/python -m pytest -q`), including `tests/test_paper_figures.py`.
  - **Page count is unverified.** `pdflatex`, `tectonic` and `latexmk` are all
    absent from this host, so no PDF was built. The owner must compile
    `docs/paper/paper.tex` on Overleaf with IEEEtran and check the four-page
    limit excluding references. Commits `f317d89`, `730b025`, `33146c4`.
- [x] Step 4. Reviewer-readiness documents (claims audit, objections,
  positioning, references to verify, threats, artifact, anonymisation).
  - Evidence: `docs/paper/CLAIMS_AUDIT.md` rewritten for the Step 3 manuscript
    with 37 claim rows (D1–D13, O1–O21, G1–G3), every row tied to a tracked
    file, plus an explicit not-claimed list and numerical consistency checks.
    `docs/paper/THREATS_TO_VALIDITY.md` rewritten around the degradation
    simulation, the confounded OSCD comparison, repeated test use, one
    checkpoint/run, interval limitations and missing artefacts.
  - `docs/paper/REVIEWER_OBJECTIONS.md` has exactly 12 objections with
    evidence-backed responses and a “do not say” list.
    `docs/paper/POSITIONING.md` contains an empty six-row published-method
    table whose cells all read “TODO - fill from original paper”; no published
    number was entered.
  - `docs/paper/REFERENCES_TO_VERIFY.md` lists 12 unique topics / 14 body
    slots, all unverified, and flags the legacy duplicate STANet entries and
    the unverified FC-Siam record without correcting them from memory.
    `docs/paper/ARTIFACT.md` gives exact setup, generation, test and hash
    commands, the current commits, seed 0/10,000 bootstrap settings, the
    unrecorded training seed, Colab status, OSCD CC BY-NC-SA legal-review
    requirement and the explicit “no code licence chosen” statement.
    `docs/paper/ANONYMISATION.md` records that the manuscript is currently
    identifying and lists what a double-blind release must remove; no history
    rewrite was performed.
  - Checks: 12 objections, 6 empty positioning rows, 12 reference topics, 37
    claims; zero prohibited priority/originality wording in `paper.tex` and the
    seven submission documents. `REPRODUCIBILITY.md` is marked historical and
    points to `ARTIFACT.md`.
  - Commits `7cc7519`, `e9607d5`, `36fd9c8`, `42755e2`.
- [x] Step 5. Twelve-slide talk, 10-minute notes, claims-on-slides, 20 Q&A,
  demo script and handout.
  - Evidence: `docs/presentation/slides.pptx` has exactly **12 slides** at
    13.333 x 7.5 in, all 12 with embedded speaker notes; rendered to PDF with
    LibreOffice and visually checked (slides 3, 7, 9, 10 and 12 rechecked after
    the final wording changes). `docs/presentation/speaker_notes.md` contains a
    1253-word script, a 9:45 timing table plus 0:15 buffer, and delivery rules;
    it is generated from the deck notes by `scripts/make_slides.py`.
  - `docs/presentation/CLAIMS_ON_SLIDES.md` maps every slide value to
    `degradation_results.csv`, `oscd_results_v2.json`, `oscd_evidence.json` or
    the paper; `docs/presentation/QA.md` has exactly **20** numbered questions
    plus the "If you do not know" instruction; `docs/presentation/DEMO.md` is a
    2:00 script with a labelled mocked-still fallback and **no committed
    recording**.
  - `docs/presentation/handout.pdf` is **one A4 page** (`595.28 x 841.89 pt`),
    built by `scripts/make_handout.py`; it includes the F1 chart, three
    key-number boxes, the OSCD line, the claim boundary and a TODO repository
    URL/DOI line. Header overlap found in QA was fixed and the page re-rendered.
  - Checks: `./venv/bin/python -m pytest -q` -> **128 passed, 3 skipped,
    1 warning in 10.27s**; a grep of the presentation docs found no "first",
    "novel", "state of the art", "one-shot", "fabricat" or "breakthrough".
    No test-city scoring, training, fine-tuning or v3 run was performed.
  - Commits `2622ec8` (deck, notes, handout, generators) and `29665ef`
    (claims audit, Q&A, demo script).
- [x] Step 6. Re-verify the app and Phase A evidence; screenshots, console
  errors, Docker; mark anything not run unverified.
  - Evidence: local server `./venv/bin/python -m uvicorn app:app --host
    127.0.0.1 --port 8010`; `GET /health` -> **200** `{"status":"ok",
    "model_present":false,"model_loaded":false,"commit":"b141712..."}`;
    `GET /model-status` -> **200** `present:false`, expected 33,268,410 bytes;
    `POST /predict` with two synthetic 64x64 PNGs -> **503** `model_unavailable`;
    `GET /history` -> **200** with the earlier synthetic entry.
  - Chrome (Playwright, headless, system Chrome) loaded the landing page:
    **5** profiles; general and agriculture both display "unvalidated,
    qualitative only" and **no "F1"** in the profile text; History renders the
    synthetic row; opening it shows "Unvalidated profile - no accuracy number
    is shown". No page JavaScript errors. The six console `ERR_FAILED` messages
    are OSM tile requests deliberately aborted to keep verification offline;
    `cdnjs.cloudflare.com` was the only external host allowed.
    Screenshots: `docs/screenshots/step6_landing.png`,
    `step6_agriculture.png`, `step6_result.png`.
  - Exports from the saved synthetic result: PDF **1 page / 3,436 bytes**
    (text begins "Decision support only - not ground truth"), CSV 115 bytes,
    GeoJSON 415 bytes. This is export wiring, **not** a new analysis.
  - `model.onnx` and `best_model.pt` are **absent**; no Google Drive mount is
    present, so no size or SHA-256 can be reported locally. `/health` and
    `/model-status` agree that the model is absent. The later Colab model check
    measured the Drive copy at 33,268,410 bytes, SHA-256 `41c2ab64...`, load
    `true`; local inference is still unverified. Docker is **not installed**
    (`docker --version` -> command not found); image build remains unverified.
  - Tests: `./venv/bin/python -m pytest -q` -> **128 passed, 3 skipped,
    1 warning in 25.11s** (same three environment skips as Step 5).
- [x] Step 7a. Create the one-click Colab hand-off notebook and its tested
  summary renderer.
  - Evidence: `notebooks/run_all_colab.ipynb` has 10 cells and no stored
    outputs; its code cells compile. It mounts Drive, unzips only the
    images/training-labels archive, clones/pulls the repository, copies the
    Drive weights, installs benchmark dependencies without exact onnx/numpy
    pins, then prints progress for (a) `pytest -q`, (b) the train-only
    `benchmarks/oscd_loco_thresholds.py`, (c) the Drive `model.onnx`
    size/SHA-256 and onnxruntime load, and (d) writes and prints
    `benchmarks/results/COLAB_RUN_SUMMARY.md`. It never unzips
    `test_labels.zip`, invokes `oscd_eval.py`, trains, fine-tunes or runs v3.
  - `benchmarks/colab_run_summary.py` renders the summary only from the saved
    LOCO JSON, model-check JSON and captured pytest line; it rejects official
    test-city leakage and missing hashes. `tests/test_colab_run_summary.py`
    (5 tests) and `tests/test_run_all_colab.py` (3 tests) cover the renderer
    and notebook structure, including the exact
    `Push skipped: copy the block above` phrase.
  - The token is read from Colab Secrets and passed to git via a temporary
    environment variable; it is not printed or written to disk. The notebook
    stops if the remote checkout lacks the Step 7 files, so the current push
    blocker must be resolved before a Colab run can succeed.
  - Full suite: **136 passed, 3 skipped, 1 warning in 18.99s**.
  - **Run on Colab 2026-10-21** at commit `e8b6678`; pytest
    `144 passed, 1 skipped, 7 warnings in 15.79s` (exit 0). Saved:
    `benchmarks/results/oscd_loco_thresholds.json` (SHA-256 `32d1dbf5...`),
    `benchmarks/results/colab_model_check.json` (SHA-256 `ec452724...`) and
    `benchmarks/results/COLAB_RUN_SUMMARY.md` (SHA-256 `77177c59...`). No test
    label was unzipped, no test city was scored, and no training, fine-tuning or
    v3 was run. The learned-classifier and auto-improvement notebooks remain
    unrun.
  - Commits `862bca5` (notebook + renderer), `0339614` (tests) and `3058466`
    (Step 7 docs). The earlier push blocker was resolved by HTTP/1.1 on
    2026-10-21; the remote then contained all commits through `e8b6678`.
- [x] Step 7b. Fill the dependent paper/docs text from the saved Colab summary,
  rebuild figures/claims audit, rerun tests, and commit locally. Trigger: the
  owner said "Colab done".
  - Evidence: both JSON hashes matched the owner-provided values
    (`32d1dbf5...`, `ec452724...`). `COLAB_RUN_SUMMARY.md` was regenerated from
    those files only, with the clean caveat line "No test city is used in this
    script."; its new SHA-256 is `77177c59...`. `docs/paper/paper.tex` now
    reports the training-only held-out F1 values (0.0976 hardcoded, 0.1469
    percentile), states that the hardcoded grid edge occurred in all 14 folds,
    and distinguishes the third training-only source file from the two test-set
    sources. `CLAIMS_AUDIT.md` adds O22 and G4 and the three source hashes.
    `ARTIFACT.md`, `SUBMISSION_NOTES.md`, `README.md`,
    `THREATS_TO_VALIDITY.md`, `REPRODUCIBILITY.md` and
    `SUBMISSION_CHECKLIST.md` were updated from the same saved files. Figures
    were rebuilt from the unchanged v2 JSON and degradation CSV. The final test
    run is recorded below. No test split was touched. The commit is local; the
    owner will push it.
- [x] End. Final tests, submission notes, unverified-claim inventory and manual
  actions.
  - Evidence: `./venv/bin/python -m pytest -q` -> **137 passed, 3 skipped,
    1 warning in 19.61s**. The three skips are `rasterio` absent, `torch`
    absent and the missing `dataset/test/A/test_100_0_0.png` sample.
  - `docs/paper/SUBMISSION_NOTES.md` records the final counts, readiness
    blockers, the numbered owner actions, the full unverified-claim list and
    the wording rules.
  - `README.md` corrected: unverified STANet/BIT rows and the comparison claim
    removed; legacy references marked unverified; the old +/-5-day catalog and
    absolute-lowest-cloud descriptions corrected to the implemented default
    +/-30-day ranked search; unverified Docker size claims removed; the
    PREREGISTRATION sentence no longer presents it as strengthening evidence
    and no longer uses the single-attempt label.
  - README correction: commit `87a7748`. The final notes/checklist commit is
    the HEAD at hand-off; the push attempt is recorded in `git log` and in the
    final report.
  - Push succeeded at `e8b6678` on 2026-10-21 after the HTTP/1.1 change; the
    Step 7b commit is local. Remote CI verification was not performed from this
    checkout. The learned-classifier and auto-improvement Colab notebooks still
    have no results.

## Manual actions for the owner

- Push the Step 7b commit (no force). The earlier HTTP 400 was fixed by using
  HTTP/1.1; the remote contains the prior history through `e8b6678`. Check the
  current count with `git rev-list --count origin/main..main`.
- The one-click Colab hand-off has run (2026-10-21 at `e8b6678`); its summary,
  LOCO result and model check are saved. Do not rerun it against test labels.
- Place the verified Drive `model.onnx` (33,268,410 bytes, SHA-256 `41c2ab64...`,
  inputs `input_a` / `input_b`) in the local checkout and verify real inference;
  do not use the invalid 60,534,573-byte file.
- Run the other Colab notebooks (`oscd_pixel_classifier.ipynb`,
  `oscd_auto_improve.ipynb`) only if those paused experiments are wanted; local
  checkout has no OSCD data and their results are unverified.
- Write and test a protocol-compliant v3 scorer **before** test access, then
  run the frozen v3 protocol once and never tune after seeing the result. The
  current checkout has no v3 scorer and no v3 output.
- Compile `docs/paper/paper.tex` with IEEEtran after replacing all
  `[CITE: ...]` placeholders; add a bibliography, author metadata and a code
  licence (none exists).
- Have an independent reviewer check the manuscript against
  `oscd_results_v2.json` and the code.
- Verify novelty in external databases using `NOVELTY_CHECKLIST.md` before any
  “novel” claim.
- Choose a target venue after checking its official scope/length/fees, and
  decide on anonymisation/preprint policy.
- Obtain a legal review of OSCD (CC BY-NC-SA), Copernicus and OpenStreetMap
  ODbL obligations before redistribution or commercial use.
- Build/run the Docker image and confirm GitHub Actions after the push issue is
  resolved; both remain unverified.
