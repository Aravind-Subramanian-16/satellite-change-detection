# Claims audit addendum — UI, profiles, reports and robustness

Date: 2026-10-21. Scope: claims introduced by the `ui-redesign`,
`analysis-profiles` and `final-polish` branches (the three-step wizard, the new
profiles, class table, PDF report, health fields, retries and cache).

`docs/paper/CLAIMS_AUDIT.md` describes the manuscript and is deliberately
**not edited** by this release. This addendum covers only new user-facing or
documentation claims. It does not re-score any benchmark and does not change
the paper's evidence status.

## Sources of record

| Source | Role |
|---|---|
| `benchmarks/results/oscd_results_v2.json` / `.md` | saved OSCD v2 scores (unchanged in this release) |
| `profiles/validation_status.json` | per-profile evidence text shown in the app and report |
| `profiles/__init__.py`, `profiles/detection.py` | thresholds and provenance strings |
| `live_pipeline.py`, `exports.py` | shared class table used by UI, CSV and report |
| `reports.py`, `tests/test_reports.py` | PDF sections, number parity and wording checks |
| `static/app.js`, `tests/test_ui.py` | UI badge logic and browser tests (Copernicus routes mocked) |
| `docs/screenshots/*` | browser screenshots from the mocked UI run |
| `benchmarks/reference_checks/` | agreement-check scripts (not run on real data here) |

## New claims

| ID | Claim (where it appears) | Evidence | Status |
|---|---|---|---|
| N1 | The buildings/roads choice carries the badge "Tested on one urban dataset" (goal picker, README, user guide) | `profiles/validation_status.json` cites OSCD urban change only, pooled F1 0.1176; app badge text is narrower than a general validation claim | Supported with the stated scope |
| N2 | "Any change", farmland, forest and water are marked "Estimate" and have no labelled evaluation (goal picker, README, limitations) | `profiles/validation_status.json` records `unvalidated, qualitative only` and `display_metrics: false` for these profiles | Supported as a not-claimed statement |
| N3 | The water profile uses NDVI/NDMI because the green band needed for NDWI is not fetched (README, limitations, profile description) | `copernicus_client.py` Evalscript fetches B02/B03/B04/B08/B11/B12 and SCL; `profiles/__init__.py` water thresholds and provenance | Supported |
| N4 | Farmland results separate "less green" from "more green"; the gain threshold is new and developer-chosen | `profiles/__init__.py` agriculture thresholds; provenance string "chosen by developer, untested"; `tests/test_profiles_phase2.py` | Supported as an implementation claim, not an evaluation |
| N5 | On-screen, CSV and PDF class numbers come from one calculation and agree | `live_pipeline.build_class_table`; `exports.py`; `reports.py`; `tests/test_reports.py` and `tests/test_live_api.py` number-parity tests | Supported by tests |
| N6 | The PDF contains a plain summary, badge reasons, images, legend, class table, settings, credits, limitations and provenance | `reports.py`; `tests/test_reports.py` checks each required section | Supported by tests |
| N7 | The data-quality badge is a heuristic with fixed reasons | `static/app.js`: cloud/shadow >10% (okay) and >30% (poor), cross-season (okay), date gap >15 days (okay) and >60 days (poor); reasons are printed next to the badge | Supported as a heuristic; not calibrated |
| N8 | Reference checks report "agreement with a reference map", never an accuracy score, and are optional | `benchmarks/reference_checks/README.md`; `tests/test_reference_check.py`; the wrapper was **not run against a real WorldCover tile** | Partially supported; real-data run unverified |
| N9 | `/health` reports CNN and spectral availability without requiring a model; retries and a bounded cache are in place | `app.py`; `copernicus_client.py`; `tests/test_robustness.py`; load test run locally (120 analysis requests), not committed as a benchmark | Supported by tests; no performance or uptime claim |
| N10 | Screenshots show the real interface, not a live satellite analysis | `tests/test_ui.py` mocks Copernicus-dependent routes; README and this addendum say so | Supported as a disclosure |

## Explicitly not claimed in this release

- That any new profile is validated, accurate or suitable for decisions without
  ground verification.
- That the app can detect individual buildings, most roads, forest type, crop
  damage versus harvest, or water extent as a flood product.
- That the built-up profile's additional NDBI/BSI cues and MMU were ablated.
- That the data-quality badge measures quality in a calibrated way.
- That the reference check has been run on real reference data or that its
  agreement percentage is an accuracy figure.
- That the Docker image was built or Cloud Run/Render was deployed from this
  checkout. Docker is not installed on the verification host.
- That retries, caching or the rate limit make the service production-grade or
  highly available; they are documented, bounded behaviours.
- That the detection algorithm, existing thresholds or existing API responses
  changed. The work adds UI, profile and report layers only.

## Wording rules for this release

- "Estimate, not ground truth" for every profile without a labelled evaluation.
- "Tested on one urban dataset" only for the buildings/roads choice, with OSCD
  named nearby.
- "Agreement with a reference map" in reference-check output; never "accuracy".
- No "AI-powered", "state of the art", "reliable" or unqualified "accurate" in
  the UI, report, README or guide.
- The word "validated" appears only inside "unvalidated" (or a negated
  statement) unless a logged evaluation file supports the exact claim.

## Reproduce the checks

```bash
./venv/bin/python -m pytest -q tests/test_reports.py tests/test_live_api.py \
  tests/test_profiles_phase2.py tests/test_ui.py tests/test_robustness.py
```

A repository-wide grep for the forbidden words is part of the final
verification; see `docs/FINAL_REPORT.md`.
