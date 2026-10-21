# Reference checks: agreement with a reference land-cover map

These scripts let a researcher compare the app's detected patches against an
independent land-cover map such as [ESA WorldCover](https://esa-worldcover.org/).

**This is a sanity check, not an accuracy measurement.** A land-cover map is a
snapshot of one date, while change detection compares two dates. The two rasters
also differ in resolution and class definitions. The output is therefore
labelled **"agreement with a reference map"**, and it should never be quoted as
an accuracy score. In particular:

- "New surface water" / "Water lost" patches are compared against the water
  class (80). This assumes the reference map predates a water-loss change;
  if it does not, the comparison is meaningless.
- "Vegetation gain / reforestation" patches are skipped: greener land can be
  cropland, grassland or shrubland, so there is no single expected class.
- "Change detected (type unclear)" and "Possible cloud interference" patches
  are skipped for the same reason.

## Files

- `agreement.py` — pure-numpy patch-vs-map comparison (`build_agreement_report`).
  Unit-tested in `tests/test_reference_check.py` with synthetic data.
- `worldcover_agreement.py` — CLI wrapper: reprojects a GeoTIFF to the analysis
  grid (needs `rasterio`, not an app dependency), compares, writes a JSON report.
  Optional `--download URL` prints the remote size and asks for confirmation
  before downloading anything.

## Getting a reference tile

ESA WorldCover 2021 (v200) is distributed as 10 m, 3°×3° tiles; the global map
runs to many GB in total, so **download only the tile(s) covering your AOI**.
Per-tile size is on the order of tens of MB — check the download page for the
current figure before fetching. Data access (AWS bucket `s3://esa-worldcover`
and the web viewer) is documented on the official
[ESA WorldCover site](https://esa-worldcover.org/); verify the current path on
that page, as bucket layouts can change.

## Usage

```bash
# 1. Save a full analysis response (the /fetch-and-predict JSON, e.g. from History)
# 2. Get the WorldCover tile covering the AOI (see above)
# 3. Run:
python worldcover_agreement.py \
    --result analysis-result.json \
    --reference ESA_WorldCover_10m_2021_v200_Map.tif \
    --out agreement-report.json
```

The report JSON contains one row per checked patch (majority reference class,
agrees yes/no) and a summary with the percentage of agreeing patches. Keep the
report next to the analysis it describes and quote both together.
