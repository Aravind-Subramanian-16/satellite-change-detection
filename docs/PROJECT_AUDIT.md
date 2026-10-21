# Project audit (Phase 0)

Date: 2026-10-21 · Commit audited: `04dbea9` · Branch: `main`

This audit was written before any redesign work. It is the evidence base for the
ui-redesign → analysis-profiles → final-polish plan in
[DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md).

## 1. Scope and method

Read in full: `app.py` (735 lines), `static/index.html`, `static/app.js`
(2020 lines), `static/app.css` (978 lines), `live_pipeline.py`,
`spectral_pipeline.py`, `profiles/__init__.py`, `profiles/detection.py`,
`profiles/validation_status.json`, `change_reasoner.py`, `reports.py`,
`exports.py`, `copernicus_client.py`, `scene_selection.py`, `geocoding.py`,
`history_store.py`, `security.py`, `provenance.py`, `postprocess.py`,
`radiometric.py`, `compositing.py`, `tiling.py`, `osm_roads.py`, and the main
test files (`test_live_api.py`, `test_profiles.py`, `test_reports.py`,
`test_exports_and_osm.py`, `test_security.py`, `test_regression_and_api.py`,
`test_model_status.py`, `test_model_load_errors.py`, `test_scene_selection.py`).

Baseline test run (fresh, this session): **137 passed, 3 skipped, 1 warning in
22.84 s**. Skips: `rasterio` not installed (OSCD label test), `torch` not
installed (finetune test), dataset sample absent (Pipeline A regression).

Live smoke test of the running server (port 8017, model absent):

- `GET /health` → 200 `{"status":"ok","model_present":false,...}`
- `POST /predict` (two valid PNGs, no model) → **503 structured JSON**
  `{"error":"Pipeline A requires an ONNX model…","code":"model_unavailable",
  "hint":"The live Sentinel-2 spectral path still works without model.onnx.",…}`
- `POST /predict` (garbage bytes) → **400 structured JSON**
  `{"error":"Could not decode the image: UnidentifiedImageError.",
  "code":"invalid_image",…}`

The server never crashed in any of these cases.

Environment facts: no `.env` file (no Copernicus credentials locally, so the
live Sentinel-2 path cannot be exercised end-to-end here), no `docker` binary,
no cached Playwright browsers (previous sessions used system Chrome), node v20
available for JS syntax checks, `model.onnx` absent locally (verified via
`/health` and `/model-status`).

## 2. Root cause: "Failed to fetch" on the Upload pair tab

**Symptom.** The user reported a raw "Failed to fetch" error on the Upload
pair tab.

**Root cause.** It is a frontend network-level failure, not a backend bug.

- `request()` in `static/app.js:202` calls `fetch()` directly with no
  `try/catch`. When the request cannot reach the server at all — server not
  running, wrong port, or the connection is reset mid-request — `fetch()`
  rejects with a `TypeError: Failed to fetch`.
- `liveErrorMessage()` (`static/app.js:269`) then echoes `error.message`
  verbatim, so the user sees the raw browser string "Failed to fetch".
- The upload submit handler (`static/app.js:1878`) catches the error and
  displays it via `showError(els.uploadError, liveErrorMessage(error))`, so the
  app does not crash — but the message is unfriendly and gives no guidance.

**Evidence the backend is fine.** The smoke test above shows every failure the
backend can produce for `/predict` (missing model, corrupt model, invalid
image, oversized file) returns structured JSON with a friendly `error`, a
`code`, and often a `hint`. The model-absent case even tells the user the
spectral path still works. So "Failed to fetch" only appears when the browser
never receives a response: server down (most common — e.g. the user opened the
page without running `uvicorn app:app`) or a mid-request worker kill (e.g. OOM
on a very large upload).

**Fix (Phase 1, additive only).** Wrap the `fetch` calls in `request()` and
`requestBlob()` with a network-level catch that converts the `TypeError` into
a friendly, actionable `Error`, e.g.: "The app could not reach the analysis
service. Is the server running? Start it with `uvicorn app:app` and refresh
the page." Keep all payload-based error handling unchanged. Add a test-visible
helper (e.g. `friendlyFetchError(error)`) and assert it in a small JS unit
test or browser check. No API behaviour changes.

## 3. Usability problems

1. **No wizard flow.** The live view is a two-panel workspace (map + settings)
   followed by hidden scene/results sections. There is no progress bar, no
   "what happens next" line, and no visual step state. `index.html` already
   numbers Steps 1–3 but nothing links them.
2. **No quality badge.** Results show a warning list but no single
   green/amber/red data-quality badge distilling cloud/shadow fraction, season
   mismatch and scene date gap with a plain reason.
3. **Dark mode only.** `static/app.css` hardcodes dark tokens in `:root` with
   no `prefers-color-scheme` or manual toggle. A light mode is required.
4. **Tiny areas show "0.00 km²".** `computeAoi()` in `app.js:493` and
   `renderAoi()` format width/height/area to 2 decimals, so a small farm field
   renders as "0.00 km²". Must use ha/acres for small areas.
5. **Jargon-first labels** (see §4). The first thing a non-expert sees in the
   settings panel is "Scene search window (± days)", "Analysis profile",
   "Minimum mapping unit (hectares)", "Radiometric normalisation".
6. **No example/demo path.** A new user must have credentials, an AOI and two
   dates before anything renders. There is no "Load an example" and no offline
   demo of the results experience.
7. **No first-time hint tour.** No skippable onboarding explaining the three
   steps.
8. **Upload tab hides its experimental status.** The model note only appears
   inside the tab; the tab label "Upload pair" gives no hint, and the results
   it produces jump the user back to the live tab (`activateTab("live")` in
   the upload submit handler).
9. **Vertical space.** The hero/intro occupies most of the first screen before
   the map on smaller laptops; the wizard design should compact it.
10. **Multi-image download UX.** "Download images" fires 5 browser downloads
    in a 250 ms sequence with no per-file progress.
11. **History hint** says "Run one from the live Sentinel-2 tab" and never
    mentions pair mode.
12. **No plain-language summary in the PDF.** The PDF starts with a key/value
    table; a one-page plain summary belongs at the top.

## 4. Jargon inventory (and planned replacements)

Required renames (master task Phase 1):

| Current label | Planned label |
| --- | --- |
| Minimum mapping unit | Ignore changes smaller than (ha) |
| Radiometric normalisation | Match brightness between dates |
| Scenes per date: temporal median | Combine several images to reduce clouds |
| Scene search window (± days) | How many days around each date to look for images |
| Analysis raster | Detail level |
| NDVI decrease / NDBI increase | Less vegetation / More built-up area |

Other jargon to soften or explain: AOI (→ "analysis area"), bbox
(→ "corner coordinates"), SCL classes 3, 8, 9, 10 (→ "pixels marked cloud or
shadow in the satellite's quality layer"), catalog cloud cover (→ "cloud cover
reported by the image catalog"), MMU (avoid in UI), Evalscript (developer
only), LEVIR-CD / OSCD / pooled F1 (→ "tested on one labelled dataset of urban
change, other types not tested"), "Decision support, not ground truth" (keep —
it is the mandated honesty phrase), "temporal median composite" (→ the
"Combine several images" wording above).

## 5. Missing features (against the master task)

1. **Water profile.** `profiles/__init__.py` has general, agriculture,
   builtup, deforestation, roads. The reasoner can label "Water body change"
   (`change_reasoner.py` rules) but there is no water analysis profile, no
   water index in the profile registry (only NDVI/NDBI/NBR/NDMI/BSI exist —
   no NDWI/MNDWI) and no shadow/season/tide warnings for water. Phase 2 must
   add a new profile with clearly named config entries and documented
   provenance ("chosen by developer, untested").
2. **Agriculture gain split.** The agriculture profile only flags loss/stress
   (`profiles/detection.py:142`); there is no "more green" class. Phase 2 must
   add a vegetation-gain flag/class additively (new threshold entry, existing
   thresholds untouched).
3. **Per-class result tables.** No "area per class, percent, total" table in
   the UI, CSV or GeoJSON; only per-region rows exist. Phase 2/3 must add a
   `class_summary` computed from region labels and surface it in all three
   places with identical numbers (additive keys/columns only).
4. **"Why we think this changed".** Per-region stats exist but no compact
   plain-English explanation per class/region. Phase 2 adds profile-aware
   wording.
5. **Reference check.** No ESA WorldCover-style "agreement with a reference
   map" step. Feasibility is questionable offline (needs large downloads);
   must state honestly if not done, and any script must live under
   `benchmarks/reference_checks/` and state download sizes first.
6. **Unified Download panel.** The actions bar exists but has no panel
   grouping; the PDF is built client-side by posting the whole result back
   (see §6 bug 3).
7. **Server-side scene caching.** None. `copernicus_client.fetch_scene`
   downloads every time. Phase 4 adds a bounded cache.
8. **Retries.** Copernicus calls have timeouts (auth 10 s, catalog 20 s,
   process 60 s) but no retries. Phase 4 adds bounded retries/backoff with
   clear messages.
9. **Light mode, hint tour, Load-an-example.** None exist.
10. **`docs/USER_GUIDE.md`.** Does not exist. Phase 5 creates it.
11. **Responsive screenshot evidence** at 375/768/1440 px does not exist for
    the current UI; Phase 1 must produce it in `docs/screenshots/`.

## 6. Bugs and latent defects

1. **Raw "Failed to fetch"** — see §2. Confirmed frontend gap.
2. **Composite mode can crash when `indices_ext` is missing.**
   `live_pipeline._fetch_window` composites `bundle["decoded_bundle"]["ext"]`
   with `median_composite` when `composite_scenes > 1`
   (`live_pipeline.py:131-141`). If Copernicus returns no `indices_ext.png`,
   `ext` is `None` and `median_composite` does `np.stack([None, …])` →
   `TypeError` → 500 `internal_error`. The fake client in tests always returns
   `indices_ext`, so this path is untested. Fix in Phase 4 with a regression
   test (fall back to the primary scene's indices when any ext is missing).
3. **Large pair-mode results cannot be exported or reported.** The CNN path
   returns full-size base64 PNGs; a large pair can produce tens of MB of JSON,
   and `POST /report` / `POST /export/{fmt}` then exceed `MAX_REQUEST_MB=60`
   (413). Fix in Phase 3: add `GET /history/{id}/report` (server-side,
   additive endpoint) and make the UI use it; keep the existing endpoints
   unchanged.
4. **Hardcoded -0.05 not in provenance.** `profiles/detection.py:162` uses a
   literal `-0.05` NDVI requirement in the builtup NDBI cue that is not part
   of `profile.thresholds`, so it never appears in provenance/report
   thresholds. Transparency fix (move to a named threshold entry) — additive.
5. **Duplicate ternary** in `buildSceneColumn` (`static/app.js:1008`):
   `input.checked = key === "before" ? A : A` — both branches identical.
   Harmless but confusing; clean up during the redesign.
6. **History list decodes full results.** `history_store.list_analyses`
   `json.load`s every stored `result_json` (including base64 images) just to
   read `percent_changed` — heavy with many rows. Minor; optional Phase 4
   improvement (store `percent_changed` in a column).
7. **OSM road raster is drawn 1 px wide regardless of pixel size**
   (`osm_roads.py:177`). At 10 m pixels roads wider than the pixel size are
   misrepresented; documented as context-only. Note, don't fix.
8. **`/history` export routes are not rate-limited.** `LIMITED_PATHS` in
   `security.py:147` covers `/export/` but not `/history/{id}/export/{fmt}`.
   Additive Phase 4 fix.
9. **Nominatim has no server-side caching**; interactive use respects the
   1/s policy naturally, but repeated search requests from many users could
   exceed it. Phase 4: tiny in-memory TTL cache, additive.

## 7. Risks to correctness

1. **Region labels are heuristics.** `change_reasoner.py` uses fixed RGB and
   index thresholds; labels like "Deforestation / vegetation loss" or "Urban
   expansion / new construction" can be wrong, especially at 10 m. The UI
   mitigates with confidence labels and honesty notes, but the new per-class
   tables (Phase 2) must reuse region labels and be clearly framed as
   heuristic classes, not a classifier.
2. **Percent-changed denominators.** `percent_changed` is the fraction of the
   whole raster (including masked pixels); `percent_changed_valid` is of valid
   pixels only. The UI and report must keep labelling these clearly ("of the
   analysed raster" vs "of valid pixels") so numbers are not misread.
3. **AOI pixel-size approximation.** The 64 px minimum (`scene_selection.py`)
   means very small AOIs are analysed at up to ~7.8 m effective pixels —
   area numbers are approximations; area in ha is computed from AOI dimensions
   and pixel counts and should be labelled approximate.
4. **Cross-season pairs.** Only a warning is emitted for the general profile;
   agriculture/deforestation interpretation genuinely requires same-season
   pairs and the profiles say so in their notes, but nothing blocks a
   cross-season run. The quality badge (Phase 1) should reflect this.
5. **Water/agriculture/forest/roads have no labelled evaluation** — the
   registry (`profiles/validation_status.json`) already states this; the new
   UI must keep surfacing "estimate, not validated" wording (global rule 4).
6. **Coverage is a bbox approximation** (`scene_selection.py:172`) and catalog
   cloud cover is scene-wide; both are labelled as such already.
7. **In-process rate limiter** is per-worker and best-effort; documented in
   `security.py`. Fine for the single-worker Cloud Run target; must stay
   documented.

## 8. Unverified items (stated honestly, never faked)

1. **Live Copernicus flow** (catalog search → scene download → analysis with
   real imagery) has never been run locally: no `.env` credentials exist on
   this machine. Verified only against the in-memory fake client in tests.
2. **CNN inference with the Drive checkpoint** (`model.onnx`, 33,268,410
   bytes) has never run locally; it loads on Colab (recorded in
   `benchmarks/results/colab_model_check.json`).
3. **Public deployment**: not deployed anywhere; Docker image not built
   (`docker` is not installed locally). `Dockerfile` and `DEPLOY.md` exist but
   are unverified.
4. **Learned pixel pipeline** (`/predict-learned`): artifact absent,
   `ENABLE_LEARNED_MODEL=0`; endpoint returns a clear 503 (code paths
   covered by tests with fakes only).
5. **OSM Overpass and Nominatim** live calls never exercised locally.
6. **The new UI design** has not been checked in a real browser yet (Phase 1
   deliverable with screenshots).
7. **Cloud Run guide** needs writing/verification (Phase 4).

## 9. Constraints respected (no-go zones, re-stated for the record)

- Never touch `docs/paper/`, the OSCD test split or labels, `best_model.pt`,
  `weights/model.onnx`, or existing files in `benchmarks/results/`.
- Never change the detection algorithm, thresholds or existing API behaviour;
  only ADD endpoints, UI and report layers.
- Never use "accurate", "validated", "AI-powered", "state of the art" or
  "reliable" unless a logged evaluation file supports the exact claim.
- Credentials only from environment variables; never printed or logged.
- No `git push`; branches `ui-redesign` → `analysis-profiles` →
  `final-polish`, small separate commits.
- The two untracked stray files `benchmarks/results/colab_run_summary.py` and
  `benchmarks/results/oscd_loco_thresholds.py` are user downloads; leave
  untracked.
