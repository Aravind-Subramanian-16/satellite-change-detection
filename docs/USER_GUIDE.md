# User guide

This guide is for people who want to use the app, not install it. It explains
what each screen asks for, how to read a result, and where the app can mislead
you. No remote-sensing background is assumed.

> **The result is an estimate.** The app compares two satellite images and
> points to places that *may* have changed. It cannot confirm what happened on
> the ground. Check important findings with local knowledge, a site visit or
> higher-resolution imagery.

## What you need

- A web browser and an internet connection (the map and satellite images are
  downloaded live).
- A free Copernicus account if you run the app yourself; a hosted copy may
  already have credentials configured. Without them, live analysis cannot run.
- An area between roughly **1 hectare and 10 km per side**. Small is better:
  a few hundred hectares is easier to interpret than a whole province.

## Step 1 — Pick an area

You can choose the area in four ways:

1. **Search a place** — type a name and pick a suggestion. The map moves there;
   then draw a box around the part you care about. Searching a whole city is
   too large for analysis.
2. **Draw a box** — use the rectangle tool to outline the area.
3. **Use current map view** — uses the visible map area. It refuses when you
   are zoomed too far out, because the area would be too large.
4. **Enter coordinates** — open "Enter coordinates manually" and type
   `west, south, east, north` in decimal degrees.

Quick-size buttons place an area of about 1, 5 or 25 hectares at the map
centre. The area readout switches between hectares, acres and km² depending on
size, and warns when the area is too small or too large.

Click **Continue: pick the dates** when the area is accepted. Not sure where to
start? **Load an example** fills the Palm Jumeirah area and two dates for you.

## Step 2 — Pick two dates and what to look for

- **What do you want to look for?** Pick one of five goals. Each card carries an
  honest evidence badge:
  - *Estimate* — the rules are transparent but have no labelled evaluation for
    that change type.
  - *Tested on one urban dataset* — only the buildings/roads choice; it was
    scored on OSCD urban change, which is not the same as your area.
- **Before date / After date** — any two dates. The app searches ±30 days
  around each by default. A wider window finds clearer images but may land
  further from the date you asked for.
- **Cross-season warning** — if the two dates fall in different seasons, a
  warning explains that crop growth, leaf cover and wetness change with the
  season and can look like damage or construction.

Open **Advanced settings** only if you need them:

| Setting | What it does |
|---|---|
| Analysis profile | The technical rule set behind the goal. The default follows your goal. |
| Ignore changes smaller than (hectares) | Removes patches below this size. Blank uses the profile default (0–0.5 ha). |
| Images per date | Combines 2–3 scenes per date to reduce clouds. Experimental; can mix dates. |
| Match brightness between dates | Compensates for overall brightness differences. Can fail when change is widespread. |
| Remove isolated specks | Cleans up single-pixel noise. |
| Mapped-road context (OSM) | Shows changed area near mapped roads as context only; this is not road detection. |

Click **Find candidate images**. For each date the app lists candidate scenes
with date, catalog cloud cover and how much of your area they cover, and marks
a recommended one. Choose one per date, then click **Run the comparison**.

## Step 3 — Read the results

The top of the results page shows a **data-quality badge**:

- **Good** — both images are mostly clear and close to your dates.
- **Okay** — use extra care. This appears when cloud/shadow is over 10%, the
  dates are in different seasons, or the clearest image landed more than 15
  days from your requested date.
- **Poor** — treat the result as a rough pointer. This appears when
  cloud/shadow is over 30% or an image landed more than 60 days from the
  requested date.

The badge states its reasons in plain words. Read them before the numbers.

Below it you will find:

- **A one-sentence summary** and summary cards (changed area, percent of the
  area, main change type).
- **What we found, by type** — a table of change types with area in hectares
  (or acres/km²), percent of the analysed area, and patch count. The same
  table appears in the CSV and the PDF.
- **Before / after** — drag the slider or use the keyboard to compare.
- **Change map** — choose Overlay, Mask or Rule evidence. The evidence layer
  is a colour scale of how strongly the rules fired; it is not a probability.
- **Changed patches** — each patch has an area and a confidence label. Open
  **Why we think this changed** for the rule that produced it.
- **How to read this result** — profile-specific caveats.
- **Greenness timeline** (farmland and general profiles) — optional NDVI
  samples over several dates; useful to see whether a drop is seasonal.
- **Where the numbers come from** — scene IDs, dates, cloud mask share,
  thresholds, app version and commit.
- **Download the results** — PDF report, GeoJSON, CSV and images.

## Worked example 1 — Farmland

Goal: find out whether a field block lost vegetation between two summers.

1. Search for the farm area, draw a box around the fields (not the whole
   district).
2. Choose **Farmland changes**.
3. Pick two dates in the **same season** (for example, mid-July in two
   consecutive years). A cross-season pair will trigger a warning and confuse
   harvest with damage.
4. Choose images with low catalog cloud cover and a high coverage percentage.
5. In the results, read the class table. The agriculture profile separates
   patches that **lost greenness** from patches that **became greener**.
6. Open **Why we think this changed** for a patch. A drop in NDVI together with
   a moisture (NDMI) drop is consistent with stress, but also with harvest,
   irrigation changes or dry weather.
7. Use **Build greenness timeline** to see whether the field regularly drops at
   that time of year.
8. Treat a single-pair result as a question to investigate, not an answer.

What can go wrong: small fields are mixed with boundaries and roads at 10 m;
harvest and bare soil look like loss; clouds and haze can mimic change; a
different crop rotation can dominate the signal. The profile has **no labelled
agriculture evaluation**.

## Worked example 2 — New construction

Goal: find new built-up surfaces at the edge of a town.

1. Draw a box around the development area, including some existing buildings
   for reference.
2. Choose **New buildings and roads**.
3. Pick a before date and an after date that bracket the construction period.
   Avoid a pair where one image is much cloudier than the other.
4. In the results, check the class table for **More built-up area** and read
   the patch explanations. The rules combine a built-up index rise, a
   bare-soil index rise and a greenness drop.
5. Open the before/after slider and confirm visually that the patch is a new
   roof or yard, not a ploughed field.
6. Use **Mapped-road context** only as a pointer to nearby roads; it does not
   detect roads.

What can go wrong: at 10 m, **individual buildings and most roads are smaller
than a pixel** and are usually missed. Bare soil, mining, landfill and
industrial roofs share spectral signatures. The built-up rules were tested on
one urban dataset (OSCD) with pooled F1 around 0.12; they were not tested on
your area or on individual structures.

## What the numbers mean

- **Percent of area** is the share of *analysed, unmasked* pixels flagged as
  changed. Cloud and shadow pixels are excluded; the masked share is shown.
- **Patch area** is the area of one connected patch on the analysis grid. It is
  an estimate from pixel counting, not a survey.
- **Minimum mapping unit (MMU)** intentionally removes small patches. "No
  patches" can mean "no change above the MMU", not "no change".
- **Confidence labels** (high/medium/low) describe how strongly the rule
  evidence agreed inside the patch; they are not probabilities.
- The report's **PDF numbers, CSV table and on-screen table come from the same
  calculation**; if they differ, that is a bug, not an alternative estimate.

## When something goes wrong

| Message or symptom | What to do |
|---|---|
| "The app could not reach the analysis service" | Check your internet connection, wait a moment and retry. The message replaces the browser's raw network error. |
| Credentials missing | Set `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` in the environment; see the README. |
| No scenes found | Widen the date window, move the dates, or check the area is not mostly ocean/cloud. |
| Scene fully masked | The chosen image is cloud-covered over your area; choose another candidate. |
| Area too large / too small | Redraw a smaller box or use a quick-size button. |
| Map does not load | Type a bounding box under "Enter coordinates manually"; the analysis still works. |
| "Failed to fetch" seen in an older version | Fixed in this release by the friendly network message above. |
| Result seems empty | Check the MMU, the data-quality badge and the season warning. Small or seasonal change may be below the filter. |

## What the app cannot do

- Resolve individual buildings, field boundaries or most roads at 10 m.
- Distinguish harvest from drought, or selective logging from fire.
- Produce a validated land-cover map, a flood assessment or a carbon estimate.
- Remove every cloud, cloud edge or terrain shadow.
- Guarantee that two images are from the exact dates you requested; check the
  scene dates shown in the result.
- Keep results private on a shared deployment: there is no login, and History
  is visible to anyone who can reach the service.

See [`LIMITATIONS.md`](LIMITATIONS.md) for the full list.

## Credits

Sentinel-2 imagery © Copernicus Data Space Ecosystem. Map tiles and place
search © OpenStreetMap contributors (ODbL), via Leaflet and Nominatim. OSCD
labels are used under their dataset terms; no model weights or benchmark data
are shipped with the app.
