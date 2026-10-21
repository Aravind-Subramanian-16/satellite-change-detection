# Definition of done — UI redesign, profiles, reports, robustness

Date: 2026-10-21 · Based on [PROJECT_AUDIT.md](PROJECT_AUDIT.md)

Completion status: **Phases 0–5 complete on `final-polish`**, with the caveats
written next to each item below. Final suite: **194 passed, 3 skipped, 1
warning**. Nothing was pushed; the merge order and the push command are in
[FINAL_REPORT.md](FINAL_REPORT.md).

## How this works

Each phase below has a checklist. A ticked box carries evidence (file, commit
hash, test count, screenshot path). Counts are from real runs in this
checkout, not estimates.

## Branch and commit policy (global rule 1)

- `main` (at `a02b27a`) → `ui-redesign` → `analysis-profiles`
  (from `ui-redesign` after its checks passed) → `final-polish` (from
  `analysis-profiles` after its checks passed).
- Small, separate commits per change. **Never `git push`.** The only pushes in
  this work were the owner-requested pushes of `main`, `ui-redesign` and
  `analysis-profiles`; the attempt to push `final-polish` was blocked by the
  permission system and was not retried. The exact command is in the final
  report.
- Audit documents (this file, PROJECT_AUDIT.md) are committed to `main`
  because they describe the pre-change baseline.

## Global honesty rules (breaking any is failure)

- [x] Do not push (no push from this phase; push of `final-polish` blocked and
      not retried)
- [x] Do not touch `docs/paper/`, the OSCD test split/labels, `best_model.pt`,
      `weights/model.onnx`, or existing `benchmarks/results/` files
      (evidence: `git diff --name-only main...final-polish -- docs/paper
      benchmarks/results weights best_model.pt model.onnx` prints nothing)
- [x] Do not merge `oscd-finetune`
- [x] Detection algorithm, thresholds and existing API behaviour unchanged —
      only ADD endpoints / UI / report layers. The one new agriculture gain
      threshold and the new water profile thresholds are additive entries in
      `profiles/__init__.py`; pre-existing threshold values are unchanged.
- [x] Forbidden words ("accurate", "validated", "AI-powered", "state of the
      art", "reliable") never appear unless a logged evaluation file supports
      the exact claim; agriculture/deforestation/water are "estimate, not
      validated". Checked in `tests/test_reports.py` and by a repository grep
      recorded in the final report; "validated" appears only as "unvalidated"
      or in negated statements.
- [x] Credentials from environment variables only; never printed or logged
      (`security.RedactingFilter`; credentials never touch the browser)
- [x] Existing tests keep passing; every new feature has tests; real counts
      are reported (final 194 passed / 3 skipped; per-branch counts below)
- [x] If something cannot be done honestly, it is said so in the final report
      (Docker build, Cloud Run deploy, real WorldCover reference run, labelled
      evaluation of the new profiles)

## Phase 0 — audit (this phase)

- [x] Read the whole frontend, backend, exports, profiles, configs and tests
      (evidence: PROJECT_AUDIT.md §1)
- [x] Diagnose the "Failed to fetch" upload error and record root cause
      (evidence: PROJECT_AUDIT.md §2 — network-level `fetch` rejection shown
      verbatim; backend verified returning structured JSON for every failure
      mode)
- [x] Baseline test run recorded (evidence: 137 passed, 3 skipped, 1 warning,
      22.84 s)
- [x] PROJECT_AUDIT.md written (usability, jargon, missing features, bugs,
      correctness risks, unverified items)
- [x] DEFINITION_OF_DONE.md written (this file)

## Phase 1 — `ui-redesign`: friendly wizard UI

Branch commits: `aba4cba` (wizard and plain language), `7b6beb3` (JS wiring),
`fbea861` (browser tests and screenshots). Branch suite at hand-off:
**140 passed, 3 skipped** (re-run in a temporary worktree with the project venv
linked; the 3 skips are the same environment skips as the baseline).

- [x] 3-step wizard (Pick area / Pick two dates / See results) with a progress
      bar, one main button per step, plain-English labels, and a "what happens
      next" line per step (evidence: `static/index.html` wizard sections;
      screenshots 01, 03, 09, 10; `tests/test_ui.py`)
- [x] Simple mode by default; "Advanced settings" collapsed (evidence:
      `<details class="advanced">` in `static/index.html`; goal picker visible)
- [x] Jargon renames from PROJECT_AUDIT.md §4 applied (evidence: labels in
      `static/index.html` and goal notes in `static/app.js`; no
      "temporal median composite" or raw "F1" in the live UI)
- [x] Area presets: "Use current map view", "Draw a box", "Search a place";
      warnings for areas under ~0.5 ha and over the limit; never "0.00 km²"
      (use ha/acres) (evidence: `computeAoi`/`formatArea` in `static/app.js`;
      screenshot 02; `test_wizard_flow_goal_sync_and_area_formatting`)
- [x] "What do you want to look for?" picker (Any change, Farmland changes,
      New buildings and roads, Forest loss, Water changes) with one-line
      descriptions and honest badges (evidence: goal cards in
      `static/index.html`; buildings badge "Tested on one urban dataset";
      tests assert no F1 in the unvalidated banner)
- [x] Results dashboard: before/after slider, change map, summary cards (area
      changed, percent of area, main change type), simple legend, one-sentence
      plain summary (evidence: screenshots 06/07/11/12;
      `test_results_dashboard_and_mobile_layout`; summary text in `reports.py`
      and UI)
- [x] Data-quality badge (green/amber/red) from cloud/shadow fraction, season
      mismatch and scene date gap, with a plain reason (evidence:
      `renderQualityBadge` in `static/app.js`; thresholds 10%/30% cloud,
      cross-season, 15/60-day gap; UI test checks the badge)
- [x] Always-visible honesty note ("Results are an automated estimate, not
      ground truth…") — shortened but never weakened; details in a "Learn
      more" panel (evidence: `#honesty-note` and `#learn-more` in
      `static/index.html`; screenshot 01)
- [x] Friendly errors for every failure, including the "Failed to fetch"
      network case from PROJECT_AUDIT.md §2 (evidence: `request()` /
      `requestBlob()` catch in `static/app.js` and show "The app could not
      reach the analysis service…"; covered by
      `test_theme_toggle_and_friendly_network_error`)
- [x] Loading states with progress text (evidence: busy overlay and
      `#live-status` / scene loading text; screenshot 05)
- [x] Responsive at 375/768/1440 px; WCAG contrast; keyboard accessible;
      dark/light mode; no horizontal scroll on mobile (evidence: screenshots
      08/09/10 and the UI test's 0 px overflow assertion; computed contrast
      ratios: dark text 17.38:1, muted 8.19:1, dim 4.86:1, blue 8.08:1; light
      text 16.34:1, muted 6.93:1, dim 4.68:1 after adjusting it from 4.35:1,
      blue 4.73:1, amber 4.60:1. No formal screen-reader audit was run.)
- [x] Skippable first-time hint tour (evidence: `#hint-tour`, `#hint-skip`,
      `#hint-next`; screenshot 01)
- [x] "Load an example" button with a built-in demo area/dates (evidence:
      `#load-example-btn`; it fills the form, but imagery still needs
      credentials and internet, so it is not an offline analysis)
- [x] Consistent design system (evidence: CSS tokens in `static/app.css`;
      all screens use the same panel/button/badge classes)
- [x] Real-browser check (system Chrome via Playwright) + screenshots saved to
      `docs/screenshots/` at 375/768/1440 px (evidence: `tests/test_ui.py`
      drives uvicorn on port 8029 and mocks Copernicus routes; screenshots
      01–12)
- [x] All existing tests still pass (evidence: 140 passed, 3 skipped at branch
      end)
- [x] New tests for new UI logic (evidence: 3 browser tests in
      `tests/test_ui.py`: wizard/area formatting, theme + friendly network
      error, results dashboard + mobile layout)

## Phase 2 — `analysis-profiles`: researcher-grade profiles

Branch commits: `cb09168` (registry, water, class table, explanations),
`4de953d` (UI class table/explanations), `24224c5` (UI tests), `5262e95`
(profile/export/reference tests), `d53cb87` (screenshots). The branch also
contains Phase 3 commits; its end-of-branch suite is **179 passed, 3 skipped**
(worktree re-run with the venv linked).

- [x] Researcher framing per profile (question, indices, known failure modes,
      honest evidence level) (evidence: `profiles/__init__.py` descriptions,
      `report_wording`, `honesty_notes`; `profiles/explanations.py`;
      `profiles/validation_status.json`)
- [x] Agriculture: veg gain/loss split ("less green"/"more green"), crop-cycle
      warning, bare-soil vs harvested vs cloud warning, area in ha (evidence:
      `ndvi_gain`, gain class in `profiles/detection.py`; warnings in
      `profile_warnings`; tests `test_agriculture_*` in
      `tests/test_profiles_phase2.py`; new threshold marked "chosen by
      developer, untested")
- [x] Buildings/roads: more built-up area, bare-soil confusion note, min area
      filter, plain statement that 10 m cannot show individual buildings or
      most roads (evidence: `profiles/__init__.py` builtup/roads notes; roads
      profile is context only; tests in `tests/test_profiles_phase2.py`)
- [x] Forest loss: size filter, regrowth vs seasonal warning (evidence:
      deforestation MMU 0.5 ha, vegetated-before rule, season warning; tests
      in `tests/test_profiles.py` and `tests/test_profiles_phase2.py`)
- [x] Water: new water profile (NDVI/NDMI ceilings, shadow/season/tides
      warnings) — additive profile only; documented as "chosen by developer,
      untested" (evidence: `profiles/__init__.py` water entry and
      `threshold_provenance`; `test_water_profile_*`)
- [x] Compact "Why we think this changed" plain explanation (evidence:
      `explain_region` in `profiles/explanations.py`; `<details>` per region
      in `static/app.js`; UI tests; screenshot 11)
- [x] Per-profile result tables (area per class, percent, total) with the same
      numbers in UI, CSV and GeoJSON (evidence: `build_class_table` in
      `live_pipeline.py`; `exports.py` class_summary block/metadata;
      `tests/test_reports.py` and `tests/test_live_api.py` parity tests)
- [x] Optional reference check (e.g. ESA WorldCover) labelled "agreement with
      a reference map", never "accuracy", with date-mismatch caveat; scripts
      under `benchmarks/reference_checks/`; download sizes stated first
      (evidence: `benchmarks/reference_checks/README.md`, `agreement.py`,
      `worldcover_agreement.py`, `tests/test_reference_check.py`; **not run
      against a real WorldCover tile in this checkout**, stated in the final
      report)
- [x] Synthetic tests: vegetation-loss patch, built-up patch, water patch —
      each asserting the right class and area; plus small-area and
      cloud-warning logic tests (evidence: `tests/test_profiles_phase2.py`:
      8 tests; `tests/test_profiles.py`)
- [x] All existing tests still pass (evidence: 179 passed, 3 skipped at branch
      end)

## Phase 3 — reports and exports (same branch, plus one final-polish commit)

Branch commits: `d967a91` (report rewrite), `0c1a994` (lint fixes), and
`a19907b` on `final-polish` (stored-analysis endpoint). Final report tests: 6
in `tests/test_reports.py` plus endpoint/parity tests in
`tests/test_live_api.py`.

- [x] PDF via one endpoint: before/after images, change map, legend,
      per-class numbers, dates, area, profile/settings in plain words, data
      credits (Copernicus, OSM ODbL), data-quality badge with reasons,
      limitations note, version/provenance (app version, git commit,
      timestamp, parameter hash), one-page plain summary at the top (evidence:
      `reports.py`; `tests/test_reports.py` checks every section)
- [x] `GET /history/{id}/report` (additive) so large pair-mode results can be
      reported without re-posting tens of MB (evidence: `app.py` route and
      `test_history_report_endpoint_returns_the_stored_pdf`; 404 for a missing
      id)
- [x] Keep GeoJSON/CSV unchanged; all three downloads in one "Download" panel
      (evidence: `_export_response` untouched in shape; `#download-panel`;
      export tests)
- [x] Tests: valid PDF, required sections, no forbidden words, graceful
      failure on missing inputs, report numbers match on-screen numbers
      (evidence: 6 tests in `tests/test_reports.py`; API test checks the PDF
      percent and class rows match the API result; empty result still renders)
- [x] All existing tests still pass (evidence: 179 passed, 3 skipped at
      `analysis-profiles` end; 193 at final)

## Phase 4 — `final-polish`: robustness

Branch commits: `f1720b5` (retries + scene cache), `6957eba` (health fields),
`3f51766` (robustness tests), `1ed6db5` (Cloud Run/cache docs), `45f6162`
(composite crash fix), `a19907b` (history report + rate limits). Branch suite:
**193 passed, 3 skipped**.

- [x] Timeouts/retries with clear messages for slow/failing Copernicus calls
      (evidence: `_post_with_retry` in `copernicus_client.py`, 3 attempts,
      exponential backoff, Retry-After; `tests/test_robustness.py`)
- [x] Bounded server-side cache for downloaded scenes (evidence:
      `_SceneCache` LRU, 64 MB / 32 entries, thread-safe; tests check hit path,
      entry bound and oversize rejection)
- [x] Rate-limit and size-limit coverage for `/history` export routes
      (evidence: `/history` added to `LIMITED_PATHS`; request-size limit
      applies to POSTs; `test_history_routes_are_rate_limited`)
- [x] Validate all inputs server-side (audit gaps fixed) (evidence: existing
      Pydantic models validate bbox/dates/window/MMU/composite; new endpoint
      returns 404 for unknown id; `/history` limit is clamped; `/report`
      rejects a non-object result. Audit bugs 4, 6 and 9 were noted as
      optional and are **not** fixed; see the final report.)
- [x] Logging never contains credentials (evidence: `RedactingFilter` and
      `tests/test_security.py` redaction tests; final grep in the report)
- [x] `/health` reports CNN availability without crashing (evidence:
      `cnn_available` / `spectral_available`; `test_health_reports_cnn_and_spectral_availability`)
- [x] If the CNN is missing, the spectral path still works and the UI says so
      plainly (evidence: `/health` fields; service status text; live path is
      independent of `model.onnx`)
- [x] Fix `median_composite` crash on missing `indices_ext` (PROJECT_AUDIT.md
      §6 bug 2) with a regression test (evidence: `compositing.py` mask
      broadcasting; `live_pipeline._fetch_window` skips the ext composite when
      absent; `test_fetch_window_composites_when_indices_ext_is_missing`;
      `test_median_composite_broadcasts_pixel_masks_across_bands`)
- [x] Dockerfile + short Cloud Run deployment guide with env-var secrets, no
      weights/credentials baked in (evidence: `DEPLOY.md` Cloud Run section,
      Secret Manager flags, max-instances 1; Dockerfile excludes weights.
      Docker is not installed locally, so the image build is **unverified**;
      stated in the final report.)
- [x] Full test suite + linter + quick load test of the main flow; fix what is
      found (evidence: 193 passed / 3 skipped; `ruff check` clean on every
      changed Python file except `app.py`, which keeps 27 pre-existing findings
      (`main`'s `app.py` had 29) — intentionally not mass-fixed; load test: 120/120 analysis
      requests and 200/200 page requests against a local server with a fake
      upstream, no failures)

## Phase 5 — documentation and honesty

- [x] README: what it is, who it is for, 5-minute quick start, credentials
      setup, tests, screenshots (evidence: `README.md`; screenshots 01/11/09)
- [x] `docs/LIMITATIONS.md` in plain language (10 m limits, clouds, seasons,
      no ground truth for most profiles, what the app can and cannot claim)
      (evidence: updated sections for water, badge heuristic, reference
      checks, reports/caching)
- [x] `docs/USER_GUIDE.md` for non-experts with worked examples (farmland,
      new construction) (evidence: new file)
- [x] Claim audit updates go to a new file, not `docs/paper/` (evidence:
      `docs/CLAIMS_AUDIT_ADDENDUM.md`; the decision is recorded in the final
      report)
- [x] `docs/FINAL_REPORT.md`: DoD checklist with evidence, exact test counts
      (passed/skipped/failed and why), per-branch commits, how to run locally
      in under 5 minutes, everything still unverified, and the exact merge
      order for the user (evidence: `docs/FINAL_REPORT.md`)

## Post-report dashboard addition (2026-10-21)

The dashboard work was finished after the first release report, without
changing the API, database schema or detection path.

- [x] History dashboard: saved-analysis count, live/upload split, simple mean
      and largest flagged share, per-analysis bars and range distribution,
      with an empty state (evidence: `renderHistoryDashboard` in
      `static/app.js`; `#history-dashboard` in `static/index.html`;
      screenshots 13–15)
- [x] Dashboard values come only from the existing `/history` fields; no new
      endpoint and no change to stored results. The UI states that the mean is
      not area-weighted and that the dashboard is not a measure of detection
      performance (evidence: dashboard note in the UI; `LIMITATIONS.md`)
- [x] Mobile navigation stays usable: at ≤480 px the tabs read Compare /
      Upload / History and all three fit at 375 px; the marketing intro is
      hidden on the History view while the honesty note remains visible
      (evidence: `test_history_dashboard_aggregates_rows_and_hides_when_empty`
      checks the tab bounds and the intro visibility)
- [x] New browser test with mocked history rows checks aggregates, range
      buckets, the empty state and 375 px overflow (evidence:
      `test_history_dashboard_aggregates_rows_and_hides_when_empty`; 4 browser
      tests in `tests/test_ui.py`)
- [x] Screenshots 13/14/15 at 1440 dark, 768 light and 375 light; 0 px
      horizontal overflow and no console errors at each width (evidence:
      `docs/screenshots/13-history-dashboard-1440.png`,
      `14-history-dashboard-768.png`, `15-history-dashboard-375.png`)
- [x] Full suite after the addition: **194 passed, 3 skipped**, 1 warning
      (evidence: `pytest -q`; 61.04 s after the change and 88.41 s on the
      final verification run; the 3 skips are unchanged environment gaps)
- [x] The dashboard screenshots use example rows from the test fixture, not
      real saved analyses; this is stated in the README (evidence: README
      screenshot disclosure)

## Final verification (before telling the user to merge)

- [x] All three branches exist in order: `ui-redesign` → `analysis-profiles`
      → `final-polish`, each with its checks green before the next was cut
      (evidence: `git log --oneline main..ui-redesign`,
      `ui-redesign..analysis-profiles`, `analysis-profiles..final-polish`;
      test counts above)
- [x] `git status` clean apart from the two known untracked stray files
      (evidence: final `git status --short` in the report; the stray files are
      `benchmarks/results/colab_run_summary.py` and
      `benchmarks/results/oscd_loco_thresholds.py`, left untouched)
- [x] No forbidden words anywhere in UI/reports/docs (evidence: grep command
      and result in the final report; the intentional "unvalidated" wording is
      the only occurrence of "validated")
- [x] No credentials or model files committed (evidence: `git show --stat` on
      the branch commits; `git diff --name-only main...final-polish` lists no
      `.env`, weights, `best_model.pt` or `model.onnx`)
- [x] Nothing under `docs/paper/`, `benchmarks/results/` (existing files),
      `weights/`, `best_model.pt` or `model.onnx` modified across the three
      branches (evidence: `git diff main...final-polish --stat` for those paths
      is empty)
- [x] Final report contains the exact merge order (evidence:
      `docs/FINAL_REPORT.md`)

## Items that are explicitly not done or not verified

- Docker image build/run: Docker is not installed on this host.
- Cloud Run/Render deployment: documented, not executed.
- Real-world reference check (ESA WorldCover): scripts and tests only; no
  download or comparison run.
- Labelled evaluation of the general, agriculture, deforestation, roads and
  water profiles: none exists here; all are labelled estimates in the UI.
- Formal screen-reader/zoom audit: not performed; contrast and keyboard paths
  were checked manually.
- Full-repository lint cleanup: pre-existing style findings remain outside the
  changed files.
- Audit bugs 4 (hardcoded built-up NDVI cue not in provenance), 6 (history list
  decodes full results) and 9 (Nominatim cache): not fixed; documented as
  optional.
