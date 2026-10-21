# Limitations and intended use

This tool is a decision-support aid for exploring Sentinel-2 change candidates.
It is not a validated land-cover product, a cadastral record, or ground truth.
The limits below are part of the result, not fine print.

## Spatial and spectral resolution

- Sentinel-2 L2A bands used here are 10–20 m (B02/B03/B04/B08 at 10 m, B11/B12
  at 20 m). A pixel is a mixture of surfaces; buildings, field boundaries,
  narrow roads and small clearings are often sub-pixel.
- The live path requests at most `MAX_ANALYSIS_PX` (default 1024) on the long
  side. AOIs are resampled to that grid, so reported pixel sizes are
  approximate and edgeless.
- B11/B12 are resampled to the 10 m grid by the data provider. Index values at
  sharp edges can be interpolated rather than measured at 10 m.
- Atmospheric correction is whatever CDSE L2A provides. The tool does not
  estimate surface reflectance, BRDF, terrain correction or sensor geometry.
- Road detection is not claimed. At 10 m, roads narrower than about 20 m are
  mostly sub-pixel; the roads profile reports change near mapped OSM roads as
  context only.

## Validation status

- Only the shared spectral/urban-change thresholding has been scored on the
  official OSCD test split. The saved source of record is
  `benchmarks/results/oscd_results_v2.json` and `.md`.
- v2 pooled results: spectral percentile F1 `0.1176` (precision `0.2419`,
  recall `0.0777`), hardcoded F1 `0.0782`, Otsu overall accuracy `0.3439` with
  `67.35%` of pixels predicted changed; true change was `5.17%`. The CNN
  joint-percentile variant reached pooled F1 `0.0007` and the reflectance
  variant `0.0000`.
- Per-city F1 varies widely (percentile ranges from `0.0005` on saclay_w to
  `0.2481` on chongqing). Ten test cities are too few for a broad
  generalisation claim.
- An earlier preliminary scoring event also used the official test split. It
  is disclosed in `PAPER_NOTES.md`; it is not an independent second test, and
  its values are not a competing final estimate.
- The `general`, `agriculture`, `deforestation` and `roads` profiles are
  unvalidated and qualitative only. The `builtup` profile is benchmarked only
  through the underlying spectral thresholding on OSCD urban change; its
  additional NDBI/BSI cues and MMU are not separately ablated. No profile has
  been validated for agriculture, forest loss, water or road labels.
- No accuracy or F1 number is shown in the interface for an unvalidated
  profile. OSCD labels cover urban change only.
- OSCD provides no Sentinel-2 SCL in the benchmark layout used here, so cloud
  and shadow exclusion was not evaluated by the benchmark. The live path does
  apply SCL masking and reports the masked fraction.
- Reported percentages are pixel shares on the analysis grid, not area
  estimates corrected for resampling, mixed pixels or map projection.

## Spectral and semantic confusion

- NDVI loss and NDBI gain are not unique to construction. Harvest, irrigation
  changes, seasonal senescence, drought, fire scars, bare soil, mining,
  shadow, haze and thin cloud can produce similar differences.
- NBR/NDVI rules cannot distinguish selective logging, clear-cut, fire and
  windthrow, and they do not establish forest type or carbon impact.
- NDVI/NDMI changes cannot distinguish crop stress from harvest, irrigation
  scheduling or normal phenology without field knowledge and a same-season,
  multi-date record.
- The built-up reasoner's construction-versus-cleared-land split is a
  deterministic heuristic, not a learned classifier.
- Water, snow, active fire and unusual surfaces are not modelled. SCL classes
  outside cloud/shadow are not otherwise corrected.
- Cloud and shadow masking is conservative: pixels flagged in either
  acquisition are excluded from valid statistics, but thin cloud, cloud edges
  and terrain shadow can remain. Masked area is excluded, never inferred.

## Temporal and geometric issues

- A single before/after pair confounds real change with season, sun angle,
  view angle, moisture and phenology. The UI warns about cross-season pairs
  but does not correct them.
- Acquisition dates can differ from the requested dates by the search window.
  The chosen scene dates and IDs are recorded in provenance; always check them.
- Co-registration is the provider's. Residual misregistration at edges can
  appear as paired change lines.
- The AOI is converted to an analysis grid; the displayed pixel size is an
  approximation. Area values are geometric AOI estimates, not classified area.
- Temporal median compositing (optional, off by default) uses the clearest
  pixels among 2–3 scenes. It can mix dates, suppress transient change, and
  still retain residual cloud; it is not validated against labels.
- PIF normalisation (optional) fits a linear gain/offset from stable pixels.
  It can fail when stable area is small, when change is widespread, or when
  the change itself is spectrally large; it is not a physical calibration.
- Morphological opening/closing and the minimum mapping unit intentionally
  remove small regions. Sub-MMU change is excluded by design and must not be
  interpreted as "no change".

## Optional learned classifier

- The learned pixel classifier is opt-in (`ENABLE_LEARNED_MODEL=1`), trained
  only on OSCD training cities, and treated as experimental. Without the
  artifact the endpoint returns 503; the spectral/live path is unaffected.
- Its artifact and OSCD data are not in this checkout. No test-city score is
  available here, and none is displayed in the interface. The Colab notebook
  is the only supported training path; its output remains unverified until it
  is run and pasted back by the owner.
- The uploaded `.npz` path accepts reflectance bands, not RGB screenshots. It
  is limited to 25 MB compressed and 4,000,000 pixels by default; larger
  scenes must be downsampled outside the app.
- A test-city leak guard rejects the ten official OSCD test cities in training
  and selection code. It cannot detect every possible leakage path (for
  example, hand-copied labels or a separately trained model).
- The CNN upload path was trained on 0.5 m LEVIR-CD aerial pairs. Transfer to
  10 m Sentinel-2 is poor in the v2 benchmark; its near-empty predictions are
  reported as measured, not hidden behind accuracy.

## Operational, privacy and security limits

- There is no user authentication or per-user isolation. Anyone who can reach
  the service can run analyses and read `/history`. If the service is
  multi-user or public, put it behind an authenticated reverse proxy and
  restrict network access.
- History stores the full result payload, including base64 preview imagery,
  filenames, AOI/place names, scene IDs and timestamps in a local SQLite file.
  Treat that file as potentially sensitive. It is not encrypted and there is
  no retention policy in the app.
- Rate limiting is in-process and per path/IP. It resets on restart, is not
  shared between workers, and is bypassed by anyone who can reach the app
  directly without the proxy. Run one worker and enforce limits at the proxy
  if exposed. `TRUST_PROXY_HEADERS=1` must only be set behind a trusted proxy.
- Upload limits are enforced in the app (type, bytes, dimensions). A reverse
  proxy should also enforce body limits; the app's `Content-Length` check does
  not cover chunked uploads.
- Credentials are read from environment variables, never embedded in the UI,
  and log records are redacted. The `/model-status` endpoint exposes local
  paths and model hashes; restrict it if paths are sensitive.
- SQLite and the OSM cache use local disk. Hosted free tiers have ephemeral
  storage and may lose history on restart. No availability, capacity or
  durability guarantee is made.
- Leaflet, Leaflet.draw and OpenStreetMap tiles are third-party services;
  their availability and terms can change. Map tiles and the CDN are loaded
  by the browser, so client IP addresses are visible to those providers.

## Data licensing

- Sentinel-2 imagery is Copernicus data. Follow the Copernicus Data Space
  Ecosystem terms and attribution requirements for any redistribution.
- OSCD labels are distributed under CC BY-NC-SA terms in the dataset used for
  this project. Commercial use and redistribution need a licence review; no
  legal conclusion is made here.
- OpenStreetMap data is © OpenStreetMap contributors and used under ODbL.
  Redistribution obligations must be verified before shipping road-context
  data.
- Model weights and benchmark data are not committed to this repository.

## What would be needed before operational use

Independent, stratified ground truth for each target; a same-season,
multi-date design; per-class confusion matrices with confidence intervals;
sensitivity analysis for thresholds and MMU; a validated cloud/shadow mask;
co-registration checks; a documented retention/privacy policy; authentication
and proxy-level limits; and a named human reviewer for every exported result.
Until then, treat every region as a candidate to verify, not a finding.
