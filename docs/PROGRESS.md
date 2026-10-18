# Project progress checklist

Evidence is recorded next to each checked item. Do not check items until the stated work or verification is complete. “Unverified” items remain unchecked, with reason/evidence noted in the phase log.

## Phase A — Finish setup and verify

- [ ] A1. Record local `model.onnx` byte size and SHA-256; do not modify it; tell user to replace it with the Drive copy of 33,268,410 bytes.
- [ ] A1. Ensure model-dependent features fail with a clear error instead of crashing.
- [ ] A2. Install dependencies in the venv using `python -m pip`.
- [ ] A2. Run `python -m pytest -q` and record exact counts.
- [ ] A3. Start the app; verify `/health`.
- [ ] A3. Verify image upload flow.
- [ ] A3. Verify dashboard rendering.
- [ ] A3. Verify before/after slider.
- [ ] A3. Verify heatmap toggle.
- [ ] A3. Verify report download.
- [ ] A3. Verify History tab.
- [ ] A3. Save screenshots under `docs/screenshots/` and record browser console errors; mark unavailable checks unverified.
- [ ] A4. Build Docker image if Docker exists; verify `/health` and PDF generation in container, or record Docker unavailable.
- [ ] A5. Add secret-free `.env.example`.
- [ ] A5. Add CPU-only Render free-tier `render.yaml` with health check.
- [ ] A5. Add `DEPLOY.md`.

## Phase B — Live map picker and best-image selection

- [ ] B1. Pin Leaflet to an exact cdnjs version; use OSM tiles with required attribution and optional Esri imagery without API keys.
- [ ] B1. Implement place search via `geocoding.py`, zoom-to-location, and an AOI box.
- [ ] B1. Enforce minimum zoom near 12 before AOI confirmation.
- [ ] B1. Enforce configurable maximum AOI dimensions of 10 km × 10 km; report area, expected pixel dimensions, too-large and too-zoomed-out states.
- [ ] B2. Add before/after date pickers and configurable ± date windows (default 30 days).
- [ ] B3. Add `/scenes` using `copernicus_client.py` to query Sentinel-2 L2A scenes intersecting each AOI/date window.
- [ ] B3. Rank scenes by AOI coverage, cloud cover, and requested-date proximity; return top five per window with date, cloud, and coverage.
- [ ] B3. Show recommended scenes, allow overrides, and warn on different seasons.
- [ ] B4. Compute AOI cloud/shadow fraction from SCL after fetch; warn above configurable 30%, suggest next scene, and preserve fully-masked error handling.
- [ ] B5. Pass AOI and selected scenes through the existing pipeline without changing detection logic.
- [ ] B6. Display pipeline, masked fraction, scene IDs/dates, and decision-support-not-ground-truth note.
- [ ] B7. Add network-free mocked-catalog pytest tests for ranking, AOI limits, season warning, and cloud warning.

## Phase C — Analysis profiles

- [ ] C0. Add profile selector to UI/API; keep general profile as unchanged default; define declarative profile configs for indices, thresholds, MMU, report wording, and honesty notes.
- [ ] C1. Agriculture: NDVI + NDMI (B08/B11), stress/vegetation-loss flags, enforced same-season warning, optional 3–5 date phenology timeline, and single-pair harvest/seasonal-confusion wording.
- [ ] C2. Deforestation: NBR (B08/B12) + NDVI drop restricted to before-image vegetation; configurable 0.5 ha default MMU; hectares per region; mandatory cloud/shadow mask.
- [ ] C3. Built-up/industrial: NDBI, built-up and bare-soil index changes plus NDVI-loss cue; use existing reasoner to classify new construction vs cleared land; identify as OSCD-overlapping profile.
- [ ] C4. Roads: state that <~20 m roads are mostly sub-pixel at 10 m and do not claim road detection; optional cached Overpass road context overlay, AOI query, attribution, ODbL verification note, and changed-area-within-X-m context only.
- [ ] C5. Add `profiles/validation_status.json`; show built-up “quantitatively benchmarked on OSCD (urban change only, pooled F1 about 0.12)” and other profiles “unvalidated, qualitative only”; never show accuracy for unvalidated profiles.
- [ ] C6. Include profile, thresholds, MMU, scenes, dates, masked fraction, code commit, validation status, and limitations in PDF reports; add GeoJSON/CSV region exports with area/type/confidence.
- [ ] C7. Add synthetic pytest coverage for each profile: index math, MMU, before-vegetation restriction, and season warning.

## Phase D — Learned model beyond CNN (OSCD train only)

- [ ] D1. Add `benchmarks/train_pixel_classifier.py` with CPU random forest or gradient boosting over both-date bands, NDVI/NDBI/NBR/NDMI/BSI differences, and 3×3/7×7 local means.
- [ ] D1. Restrict training/model selection to 14 OSCD train cities; use fixed seeded three-city validation; choose class weight/threshold there; enforce no test-city reads.
- [ ] D2. Score the 10 test cities once; write separate `oscd_results_v3.json/.md` with metrics and predicted/true fractions, labelled “learned pixel classifier (OSCD train)”; disclose third test-split scoring.
- [ ] D3. Save joblib outside git and add optional app loader/flag; keep explainable spectral default.
- [ ] D3. Add `notebooks/oscd_pixel_classifier.ipynb` aligned with OSCD benchmark setup; do not run locally; v3 results stay unverified until user supplies Colab output.
- [ ] D4. Add synthetic feature-builder and no-test-city-guard tests.

## Phase E — Production hardening

- [ ] E1. Validate upload type, size, and dimensions; rate-limit; enforce strict CORS/security headers; keep secrets out of logs; add structured logs and request IDs.
- [ ] E1. Run Docker as non-root; pin compatible dependency ranges for Colab; do not pin onnx in runtime requirements; keep onnx in dev requirements only.
- [ ] E2. Add GitHub Actions pytest workflow; model-dependent tests skip cleanly.
- [ ] E3. Review accessibility/UX: keyboard slider, color-blind-safe heatmap, legends/units, loading/errors for bad file/Copernicus/no imagery/fully masked/oversized AOI, responsive layout, empty states.
- [ ] E4. Add provenance to every result: code commit, pipeline, profile, thresholds, scenes, dates, masked fraction, timestamp.
- [ ] E5. Add user-facing `docs/LIMITATIONS.md` covering 10 m resolution, seasonal confusion, clouds, and no ground-truth guarantee.

## Phase F — Paper and presentation

- [ ] F1. Create `docs/paper/paper.tex` using IEEEtran: abstract, introduction, related-work placeholders, methods, experiments, results tables from saved JSON, discussion, limitations, conclusion.
- [ ] F1. Cover LEVIR-CD 0.5 m CNN, spectral+SCL hardcoded/Otsu/percentile, reasoner, profiles, map/AOI best-scene Copernicus workflow, and learned classifier.
- [ ] F2. Frame contribution honestly as reproducible deployed hybrid 10 m benchmark; CNN transfer F1 ~0.0007; spectral best ~0.12 but weak; not state-of-the-art; domain gap hypothesis; explain Otsu over- and tuned-threshold under-prediction; disclose two test scoring events (three after v3); state three non-built-up profiles are unvalidated.
- [ ] F3. Use `[CITE: topic]` placeholders only; maintain `docs/paper/TODO_CITATIONS.md`; invent no citations, DOIs, impact factors, baselines, or acceptance rates.
- [ ] F4. Add `scripts/make_paper_figures.py` reading saved JSON for per-city F1, predicted-vs-true fraction, precision-recall scatter, and qualitative placeholder; add fake-JSON test.
- [ ] F5. Add `CLAIMS_AUDIT.md`, `THREATS_TO_VALIDITY.md`, `REPRODUCIBILITY.md`; include commands, commits, seeds, Colab steps, and OSCD CC BY-NC-SA/commercial-use legal-review note.
- [ ] F6. Add `docs/paper/VENUES.md` describing venue types/expectations; explicitly require official verification of scope, length, fees; no impact factors/acceptance rates.
- [ ] F7. Add `docs/presentation/slides.md` with 12 slides, speaker notes, live demo script; add `docs/presentation/QA.md` with 20 honest reviewer/panel Q&As.
- [ ] F8. Include future work: human-feedback labels, CNN fine-tuning on OSCD train, labeled agriculture/deforestation data, higher-resolution roads imagery.

## Phase commit and push log

- Initial checklist commit: pending.
- Phase A commit/push: pending.
- Phase B commit/push: pending.
- Phase C commit/push: pending.
- Phase D commit/push: pending; v3 is not run locally.
- Phase E commit/push: pending.
- Phase F commit/push: pending.

## Manual actions for the owner

- Pending; list exact requirements here as phases are verified.
