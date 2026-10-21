# Project progress

Status legend: `[x]` verified with evidence below it, `[ ]` not verified.
Evidence must be a command output or a committed file path. No benchmark number
appears here without a local result file behind it.

Checkout state (2026-10-21): `model.onnx`, `best_model.pt`, the OSCD imagery and
the learned joblib are **absent from this local checkout**. The ONNX file present
during the owner's earlier Phase A run measured 60,534,573 bytes and failed
protobuf loading; it is not the verified 33,268,410-byte Drive copy. The v2
benchmark result files are now present.

## Phase A — Finish setup and verify

- [x] A1. Record the local `model.onnx` byte size and SHA-256; do not modify it;
  tell the owner to replace it with the Drive copy of 33,268,410 bytes.
  - Evidence (owner's earlier environment): `stat -f 'size_bytes=%z' model.onnx
    && shasum -a 256 model.onnx` → `60534573`; SHA-256
    `b3d95e3e796b3bda4b06dc37a4909a47be8b6c13460b59fed3d6f4a66e2ececd`.
    That file was invalid; replacement is still required. The file is absent
    from the current checkout, so `/model-status` reports `present: false`.
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
  - Evidence: `docs/paper/paper.tex` (IEEEtran conference): abstract,
    introduction, related work with `[CITE: ...]` slots, data/task, methods,
    protocol/scoring history, results using generated tables, validation-only
    ablations, discussion with future work, limitations,
    reproducibility/ethics, conclusion and appendix. It was **not compiled**:
    no `pdflatex`/`tectonic`/`latexmk` on this host.
- [x] F2. Honest framing (negative transfer: aggregate CNN F1 0.0007; spectral
  percentile F1 0.1176, hardcoded 0.0782, Otsu F1 0.0953 with OA 0.3439 as its
  headline; two prior test-scoring events disclosed; third preregistered as v3
  and uncomputed; four non-built-up profiles unvalidated).
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
  - Evidence: `scripts/make_paper_figures.py` strictly validates 10 cities ×
    5 methods and writes six PNGs, three `.tex` tables and
    `figure_manifest.json` (v2 hash
    `37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f`).
    Ablation/reliability are labelled placeholders without inputs. Five tests
    in `tests/test_paper_figures.py`, including rejection of missing methods,
    duplicates and non-test rows.
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

## Manual actions for the owner

- Replace the invalid 60,534,573-byte `model.onnx` with the verified
  33,268,410-byte Drive copy and confirm input names `input_a`, `input_b`.
- Run the Colab notebooks (`oscd_pixel_classifier.ipynb`,
  `oscd_auto_improve.ipynb`) and paste the outputs; local checkout has no OSCD
  data.
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
