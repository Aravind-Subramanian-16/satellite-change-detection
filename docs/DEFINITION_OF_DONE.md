# Definition of done — UI redesign, profiles, reports, robustness

Date: 2026-10-21 · Based on [PROJECT_AUDIT.md](PROJECT_AUDIT.md)

## How this works

Each phase below has a checklist. Tick `[x]` only with evidence (file, commit
hash, test count, screenshot path). This file is updated as work progresses and
is the source for the final report.

## Branch and commit policy (global rule 1)

- `main` (at `04dbea9`) → create `ui-redesign` → create `analysis-profiles`
  (from ui-redesign after its checks pass) → create `final-polish` (from
  analysis-profiles after its checks pass).
- Small, separate commits per change. **Never `git push`.**
- Audit documents (this file, PROJECT_AUDIT.md) are committed to `main`
  because they describe the pre-change baseline.

## Global honesty rules (breaking any is failure)

- [x] Do not push (no push so far; continues for every phase)
- [x] Do not touch `docs/paper/`, the OSCD test split/labels, `best_model.pt`,
      `weights/model.onnx`, or existing `benchmarks/results/` files
- [x] Do not merge `oscd-finetune`
- [x] Detection algorithm, thresholds and existing API behaviour unchanged —
      only ADD endpoints / UI / report layers
- [x] Forbidden words ("accurate", "validated", "AI-powered", "state of the
      art", "reliable") never appear unless a logged evaluation file supports
      the exact claim; agriculture/deforestation/water/roads are "estimate,
      not validated"
- [x] Credentials from environment variables only; never printed or logged
- [x] Existing tests keep passing; every new feature has tests; report real
      counts
- [x] If something cannot be done honestly, it is said so in the final report

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

Checklist (all items need evidence):

- [ ] 3-step wizard (Pick area / Pick two dates / See results) with a progress
      bar, one main button per step, plain-English labels, and a "what happens
      next" line per step
- [ ] Simple mode by default; "Advanced settings" collapsed
- [ ] Jargon renames from PROJECT_AUDIT.md §4 applied
- [ ] Area presets: "Use current map view", "Draw a box", "Search a place";
      warnings for areas under ~0.5 ha and over the limit; never "0.00 km²"
      (use ha/acres)
- [ ] "What do you want to look for?" picker (Any change, Farmland changes,
      New buildings and roads, Forest loss, Water changes) with one-line
      descriptions and honest badges ("Estimate, not validated" /
      "Tested on one urban dataset only" for builtup)
- [ ] Results dashboard: before/after slider, change map, summary cards (area
      changed, percent of area, main change type), simple legend, one-sentence
      plain summary
- [ ] Data-quality badge (green/amber/red) from cloud/shadow fraction, season
      mismatch and scene date gap, with a plain reason
- [ ] Always-visible honesty note ("Results are an automated estimate, not
      ground truth…") — shortened but never weakened; details in a "Learn
      more" panel
- [ ] Friendly errors for every failure, including the "Failed to fetch"
      network case from PROJECT_AUDIT.md §2 (request()/requestBlob() catch +
      plain message; never a raw browser string)
- [ ] Loading states with progress text
- [ ] Responsive at 375/768/1440 px; WCAG contrast; keyboard accessible;
      dark/light mode; no horizontal scroll on mobile
- [ ] Skippable first-time hint tour
- [ ] "Load an example" button with a built-in demo area/dates (works offline
      where possible)
- [ ] Consistent design system
- [ ] Real-browser check (system Chrome via Playwright) + screenshots saved to
      `docs/screenshots/` at 375/768/1440 px
- [ ] All existing tests still pass (record count)
- [ ] New tests for new UI logic (record count)

## Phase 2 — `analysis-profiles`: researcher-grade profiles

- [ ] Researcher framing per profile (question, indices, known failure modes,
      honest evidence level)
- [ ] Agriculture: veg gain/loss split ("less green"/"more green"),
      crop-cycle warning, bare-soil vs harvested vs cloud warning, area in ha
      (new thresholds in clearly named config entries with documented
      provenance; existing thresholds untouched)
- [ ] Buildings/roads: more built-up area, bare-soil confusion note, min area
      filter, plain statement that 10 m cannot show individual buildings or
      most roads
- [ ] Forest loss: size filter, regrowth vs seasonal warning
- [ ] Water: new water profile (water index, shadow/season/tides warnings) —
      additive profile only; documented as "chosen by developer, untested"
- [ ] Compact "Why we think this changed" plain explanation
- [ ] Per-profile result tables (area per class, percent, total) with the same
      numbers in UI, CSV and GeoJSON (additive fields only)
- [ ] Optional reference check (e.g. ESA WorldCover) labelled "agreement with
      a reference map", never "accuracy", with date-mismatch caveat; scripts
      under `benchmarks/reference_checks/`; download sizes stated first; if
      not feasible, say so in the final report
- [ ] Synthetic tests: vegetation-loss patch, built-up patch, water patch —
      each asserting the right class and area; plus small-area and
      cloud-warning logic tests (record count)
- [ ] All existing tests still pass (record count)

## Phase 3 — reports and exports (same branch)

- [ ] PDF via one endpoint: before/after images, change map, legend,
      per-class numbers, dates, area, profile/settings in plain words, data
      credits (Copernicus Sentinel, OSM ODbL), data-quality badge with
      reasons, limitations note, version/provenance (app version, git commit,
      timestamp, parameter hash), one-page plain summary at the top
- [ ] `GET /history/{id}/report` (additive) so large pair-mode results can be
      reported without re-posting tens of MB (PROJECT_AUDIT.md §6 bug 3)
- [ ] Keep GeoJSON/CSV unchanged; all three downloads in one "Download" panel
- [ ] Tests: valid PDF, required sections, no forbidden words, graceful
      failure on missing inputs, report numbers match on-screen numbers
      (record count)
- [ ] All existing tests still pass (record count)

## Phase 4 — `final-polish`: robustness

- [ ] Timeouts/retries with clear messages for slow/failing Copernicus calls
- [ ] Bounded server-side cache for downloaded scenes
- [ ] Rate-limit and size-limit coverage for `/history` export routes
      (additive)
- [ ] Validate all inputs server-side (audit gaps fixed)
- [ ] Logging never contains credentials (verify with a grep + existing
      redaction tests)
- [ ] `/health` reports CNN availability without crashing (already verified in
      Phase 0; keep the regression tests green)
- [ ] If the CNN is missing, the spectral path still works and the UI says so
      plainly
- [ ] Fix `median_composite` crash on missing `indices_ext` (PROJECT_AUDIT.md
      §6 bug 2) with a regression test
- [ ] Dockerfile + short Cloud Run deployment guide with env-var secrets, no
      weights/credentials baked in (note: docker is not installed locally, so
      the image build itself is verified by inspection only — stated in the
      final report)
- [ ] Full test suite + linter + quick load test of the main flow; fix what is
      found (record counts)

## Phase 5 — documentation and honesty

- [ ] README: what it is, who it is for, 5-minute quick start, credentials
      setup, tests, screenshots
- [ ] `docs/LIMITATIONS.md` in plain language (10 m limits, clouds, seasons,
      no ground truth for most profiles, what the app can and cannot claim)
- [ ] `docs/USER_GUIDE.md` for non-experts with worked examples (farmland,
      new construction)
- [ ] Claim audit updates go to a new file, not `docs/paper/` (global rule 2
      wins; the decision is recorded in the final report)
- [ ] `docs/FINAL_REPORT.md`: DoD checklist with evidence, exact test counts
      (passed/skipped/failed and why), per-branch commits, how to run locally
      in under 5 minutes, everything still unverified, and the exact merge
      order for the user

## Final verification (before telling the user to merge)

- [ ] All three branches exist in order: `ui-redesign` → `analysis-profiles`
      → `final-polish`, each with its checks green before the next was cut
- [ ] `git status` clean apart from the two known untracked stray files
- [ ] No forbidden words anywhere in UI/reports/docs (grep evidence)
- [ ] No credentials or model files committed (evidence: `git show --stat`)
- [ ] Nothing under `docs/paper/`, `benchmarks/results/` (existing files),
      `weights/`, `best_model.pt` or `model.onnx` modified across the three
      branches (evidence: `git diff main...final-polish --stat`)
- [ ] Final report contains the exact merge order
