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
    `./venv/bin/python -m pytest -q` → **33 passed, 1 skipped, 1 warning in
    2.95s**. The skip is the Pipeline A regression test requiring `model.onnx`.
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

- [ ] B1. Leaflet pinned to an exact cdnjs version with OSM tiles (optional Esri
  World Imagery), correct attribution, no API keys; place search/geocoding,
  zoom-to-location, AOI box; minimum zoom ~12 before confirmation; maximum AOI
  10 km × 10 km configurable; AOI area in km² and expected pixel dimensions;
  clear too-large / too-zoomed-out messages.
- [ ] B2. Before/after date pickers with a ± window (default 30 days).
- [ ] B3. `/scenes` queries the Copernicus catalog for Sentinel-2 L2A scenes
  intersecting the AOI per window; ranks by AOI coverage, cloud cover and
  closeness to requested date; returns top 5 per window with date, cloud % and
  coverage %; UI shows a “recommended” badge and allows override; warns when the
  two dates fall in different seasons.
- [ ] B4. After fetching, compute cloud and shadow fraction over the AOI from
  SCL; above a configurable 30% warn and suggest the next-best scene; fully
  masked uses the existing error state.
- [ ] B5. Pass AOI and chosen scenes through the existing pipeline without
  changing detection logic in this phase.
- [ ] B6. UI shows pipeline used, percent masked, scene IDs and dates, and a
  decision-support-not-ground-truth note.
- [ ] B7. pytest tests with mocked catalog responses covering ranking, AOI
  limits, season warning and cloud warning.

## Phase C — Analysis profiles

- [ ] C0. Add an analysis-profile selector to UI and API; each profile is a
  small declarative config (indices, thresholds, MMU, report wording, honesty
  notes) on top of `spectral_pipeline.py` and `change_reasoner.py`; general
  profile remains default and unchanged.
- [ ] C1. Agriculture: NDVI and NDMI difference, cropland stress /
  vegetation-loss flags, enforced same-season warning, optional 3–5 date NDVI
  timeline; report wording explains that single-pair differences confuse
  harvest/season cycles with damage.
- [ ] C2. Deforestation: NBR and NDVI drop restricted to pixels vegetated in the
  before image, configurable MMU (default 0.5 ha), area in hectares per region,
  mandatory cloud/shadow masking.
- [ ] C3. Built-up/industrial: NDBI, built-up index and bare-soil index change
  with an NDVI-loss cue; existing change reasoner distinguishes new construction
  from cleared land.
- [ ] C4. Roads: UI/docs state that roads narrower than ~20 m are mostly
  sub-pixel at 10 m; do not claim road detection; optional cached OSM/Overpass
  road overlay with attribution and ODbL caveat; report “changed area within X m
  of mapped roads” as context only.
- [ ] C5. Validation-status badge from `profiles/validation_status.json`:
  built-up “quantitatively benchmarked on OSCD (urban change only, pooled F1
  about 0.12)”; all others “unvalidated, qualitative only”; never show accuracy
  numbers for unvalidated profiles.
- [ ] C6. PDF reports include profile, thresholds, MMU, scene IDs, dates,
  percent masked, code commit hash, validation status and limitations; add
  GeoJSON and CSV exports of regions with area, type and confidence.
- [ ] C7. pytest tests on synthetic arrays for each profile (index math, MMU,
  vegetated-before restriction, season warning).

## Phase D — Learned model beyond the CNN (OSCD train only)

- [ ] D1. `benchmarks/train_pixel_classifier.py`: gradient-boosted trees or
  random forest (scikit-learn, CPU) on per-pixel band reflectances for both
  dates, NDVI/NDBI/NBR/NDMI/BSI differences, and 3×3/7×7 local means; train on
  14 OSCD TRAIN cities with 3 fixed seeded held-out train cities; never read the
  10 test cities during training/selection.
- [ ] D2. Save the model as a small joblib file outside git; loader available to
  the app as an optional “learned” pipeline behind a flag; explainable spectral
  pipeline stays default.
- [ ] D3. `notebooks/oscd_pixel_classifier.ipynb` matching `oscd_benchmark.ipynb`
  setup; not run locally; results unverified until owner pastes Colab output.
- [ ] D4. Tests with synthetic data for the feature builder and the no-test-city
  guard.
- [ ] D5. Test-set scoring deferred to Phase D2 step 6 for pre-registered
  systems only.

## Phase D2 — X-factors and autonomous accuracy improvement

- [ ] D2.1. `docs/paper/XFACTORS.md`: differentiators, evidence needed, prior-work
  comparison topics as `[CITE: topic]`, status implemented/partial/idea.
- [ ] D2.2. Implement behind flags, each with a synthetic-data test, default
  pipeline unchanged: (a) radiometric normalisation, (b) temporal median
  compositing, (c) morphological cleanup + object MMU, (d) CNN fine-tuning on
  OSCD train only (new file, never `best_model.pt`), (e) fusion/stacking, (f)
  uncertainty from model agreement with ECE on held-out train cities.
- [ ] D2.3. `benchmarks/auto_improve.py`: fixed search space/seeds,
  leave-city-out CV over 14 train cities, hard trial budget, every trial logged
  to `benchmarks/results/auto_improve_log.json` including failures, selection by
  validation F1 only, guard that raises if any test city is read, ablation tables
  on validation only.
- [ ] D2.4. `notebooks/oscd_auto_improve.ipynb` (Colab); not run locally; gains
  unverified until owner pastes output.
- [ ] D2.5. `docs/paper/PREREGISTRATION.md` committed before any test scoring,
  listing exact systems, metrics and selection rule.
- [ ] D2.6. Score the 10 test cities ONCE for pre-registered systems into
  `oscd_results_v3.json/.md` without overwriting v2; record the third scoring; no
  tuning/reselection after seeing results. **Blocked: OSCD data and weights
  absent locally; only Colab can run it.**
- [ ] D2.7. Report improvements with variance across cities; drop and log
  components that do not help on validation.

## Phase E — Production hardening

- [ ] E1. Upload validation (type, size, dimensions), rate limiting, strict
  CORS, security headers, no secrets in logs, structured logging, request IDs,
  non-root Docker user, pinned compatible dependency ranges that install on
  Colab (no onnx pin; onnx only in `requirements-dev.txt`).
- [ ] E2. GitHub Actions workflow running pytest on push with model-dependent
  tests skipped cleanly.
- [ ] E3. Accessibility/UX review: keyboard slider, colour-blind-safe heatmap,
  legends/units, loading and error states for every failure, responsive layout,
  empty states.
- [ ] E4. Provenance on every result: commit hash, pipeline, profile,
  thresholds, scene IDs, dates, percent masked, timestamp.
- [ ] E5. `docs/LIMITATIONS.md`: 10 m resolution, seasonal confusion, clouds,
  no ground-truth guarantee.

## Phase F — Paper and presentation

- [ ] F1. `docs/paper/paper.tex` (IEEEtran) with abstract, introduction,
  related work placeholders, methods, experiments, results tables generated from
  JSON, ablations, discussion, limitations, conclusion.
- [ ] F2. Honest framing (negative transfer: aggregate CNN F1 0.0007; spectral
  percentile F1 0.1176, hardcoded 0.0782, Otsu 0.0953; two test scoring events
  in v2, third planned in v3; three non-built-up profiles unvalidated).
- [ ] F3. `[CITE: topic]` placeholders and `docs/paper/TODO_CITATIONS.md`; no
  invented references or baselines.
- [ ] F4. `scripts/make_paper_figures.py` reading saved JSON and writing
  `docs/paper/figures/` (per-city F1, predicted vs true fraction,
  precision–recall, ablation, reliability, qualitative placeholder); test with
  fake JSON.
- [ ] F5. `CLAIMS_AUDIT.md`, `THREATS_TO_VALIDITY.md`, `REPRODUCIBILITY.md`
  (commands, hashes, seeds, Colab steps, OSCD CC BY-NC-SA and commercial-use
  caveat).
- [ ] F6. `NOVELTY_CHECKLIST.md` with 3–5 searches per claimed contribution,
  databases, status unverified.
- [ ] F7. `VENUES.md` with venue types and expectations; scope/length/fees
  flagged for verification; no impact factors or acceptance rates.
- [ ] F8. `SUBMISSION_CHECKLIST.md`: anonymisation, data/code availability,
  licences, ethics/dual-use, contributions, arXiv decision, AI-assistance
  disclosure.
- [ ] F9. `docs/presentation/slides.md` (12 slides, speaker notes, live-demo
  script) and `docs/presentation/QA.md` (20 honest reviewer questions).
- [ ] F10. Future work: human-feedback loop, labelled agriculture/deforestation
  data, higher-resolution roads, unfinished D2 ideas.

## Phase commit and push log

- Phase A checkpoint: rebased onto remote v2 results; commit hash recorded in
  `git log` (message begins “feat: harden model fallback”). Push attempted.
- Phase B commit/push: pending.
- Phase C commit/push: pending.
- Phase D commit/push: pending; v3 is not run locally.
- Phase E commit/push: pending.
- Phase F commit/push: pending.

## Manual actions for the owner

- Replace the invalid 60,534,573-byte `model.onnx` with the verified
  33,268,410-byte Drive copy and confirm input names `input_a`, `input_b`.
- Run the Colab notebooks (`oscd_pixel_classifier.ipynb`,
  `oscd_auto_improve.ipynb`) and paste the outputs; local checkout has no OSCD
  data.
- Verify novelty in external databases using `NOVELTY_CHECKLIST.md` before any
  “novel” claim.
- Choose a target venue after checking its official scope/length/fees.
- Obtain a legal review of OSCD (CC BY-NC-SA) and OpenStreetMap ODbL
  obligations before redistribution or commercial use.
