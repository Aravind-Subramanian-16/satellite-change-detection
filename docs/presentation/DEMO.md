# Two-minute demo script

The demo is optional. It shows the decision-support interface and its
validation/provenance guardrails. It is **not** a real Copernicus analysis and
must not be presented as one.

## Preflight (before the session)

1. Start a local server only:
   ```bash
   ./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8010
   ```
2. Open `http://127.0.0.1:8010/` and check `GET /health`.
3. Check whether a valid `model.onnx` is present and loads. If it is absent or
   invalid, `/predict` returns a service error by design; do **not** click
   Predict during the talk.
4. Do not use live Copernicus fetching unless `COPERNICUS_CLIENT_ID` and
   `COPERNICUS_CLIENT_SECRET` are set in the environment and a real request has
   been tested. Do not display credentials.
5. Confirm which screenshots carry the visible "MOCKED API RESPONSES / MOCKED
   DATA" banner. If using them, say the word "mocked" out loud.

If any check fails, use the still-image fallback below. Do not improvise a
result or show a cached result as live.

## Script (2:00)

### 0:00-0:15 - Frame the demo

> "This is a prototype interface, not a validated service. I am going to show
> two guardrails: it withholds accuracy for profiles that have not been
> quantitatively validated, and it records where every result came from. I will
> not show a detection score."

Show the landing view. Do not start with the model or a heatmap.

### 0:15-0:45 - Show the input path and its limits

- Point to the map and OSM attribution.
- Draw or select a small AOI; point to the area in km² and the expected pixel
  dimensions. Mention the 10 km × 10 km cap.
- Point to the date controls and the scene-selection step.
- Say: "This path serves Sentinel-2 at 10 m. The paper's warning is exactly
  that a native-resolution score does not validate this path."

If the live scene search is not configured, do not click it. Say: "Scene search
needs Copernicus credentials and is not part of this recording."

### 0:45-1:15 - Show validation gating

- Switch to the agriculture (or another non-urban) profile.
- Point to the badge and banner: "Quantitatively unvalidated" / "no accuracy
  number is shown".
- Say: "The interface deliberately shows no F1 here. Only profiles with saved
  benchmark evidence can display a quantitative score."
- Do not display an accuracy number for an unvalidated profile.

### 1:15-1:40 - Show provenance

Open the result panel or the mocked result still. Point to the Provenance block:
commit, app version, pipeline, profile, scene IDs, dates, AOI bbox, cloud/shadow
masked percent and UTC timestamp.

> "This is the audit trail. Without these fields a polygon is not reviewable.
> The same fields travel into the exports."

If the view is a mocked still, say: "This screenshot is mocked UI wiring, not a
real analysis."

### 1:40-1:55 - Show exports

- Point to "Download PDF report", "Export GeoJSON" and "Export CSV".
- Say: "The exports repeat the provenance so a result can be reconstructed
  outside the browser."

### 1:55-2:00 - Close

> "The demo shows the reporting discipline, not detection accuracy. The paper's
> quantitative evidence is the saved degradation and OSCD results."

Stop. Do not take questions while a live request is running.

## Pre-recorded fallback

No demo recording is committed in this checkout. Record one before using this
section in a talk; until then use the still images.

**Recording recipe (owner action)**

- Resolution 1920x1080, 30 fps, no notifications, no credentials visible.
- Start at the landing page. Follow the 2:00 script above.
- Keep the "MOCKED API RESPONSES / MOCKED DATA" banner visible if any result is
  mocked.
- Do not record a Predict request unless `model.onnx` loads and the request
  succeeds locally.
- End on the provenance block or the exports, not on a heatmap.
- Save as `docs/presentation/demo_fallback.mp4` and record its SHA-256 in
  `docs/presentation/ARTIFACTS.md` if that file is created.

**Still-image fallback (available now)**

Use these files in this order:

1. `docs/screenshots/phase_b_live.png` - map/AOI and scene panel.
2. `docs/screenshots/phase_b_scenes.png` - scene candidates.
3. `docs/screenshots/phase_b_results.png` - validation banner, provenance and
   exports. The banner says "MOCKED API RESPONSES - UI DEMONSTRATION, NOT A REAL
   ANALYSIS."
4. `docs/screenshots/phase_b_mobile.png` - responsive layout, if asked.

Say explicitly: "These images prove UI wiring with mocked API responses. They
are not a Copernicus analysis and not a model result."

Do not show `phase_a_dashboard.png` or `phase_a_landing.png` as evidence of a
validated workflow; they document an earlier phase and may not carry the mock
banner. If you use them, label them as historical UI screenshots.

## What not to do

- Do not say "the model detects change in this AOI" while showing mocked data.
- Do not show a number for an unvalidated profile.
- Do not show `.env`, tokens, client IDs, local paths with usernames, or
  terminal history.
- Do not run a live Copernicus request on conference Wi-Fi.
- Do not claim the app was validated end to end. It was not.
- Do not use the demo to introduce a result that is not in the paper.

## If the demo fails on stage

Say: "The live interface is not available; I will use the saved UI stills,
which are mocked and labelled as such." Switch to the still-image fallback and
continue at 0:15 of the script. If the stills are also unavailable, skip the
demo and return to slide 7. The talk does not depend on the demo.
