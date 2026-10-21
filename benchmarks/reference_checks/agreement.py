"""Agreement between detected change patches and a reference land-cover map.

This is a coarse sanity check, not a performance measurement. A land-cover
map is a snapshot of one date, while change detection compares two dates, so
the reference class only describes one side of the change. "Water lost"
patches, for example, are compared against the water class on the assumption
that the reference map predates the change — if it does not, the comparison
is not meaningful. Report this as "agreement with a reference map", never as
an accuracy score.

Pure numpy: the reference map must already be aligned to the analysis raster
(an integer HxW array of land-cover class codes). The CLI wrapper in
worldcover_agreement.py performs the geospatial alignment.
"""
from __future__ import annotations

import numpy as np

#: change_type -> {reference class name: class code}. Codes follow ESA
#: WorldCover numbering; other legends can be mapped via the class_names
#: argument.
EXPECTED_CLASSES: dict[str, dict[str, int]] = {
    "New surface water": {"water": 80},
    "Water lost": {"water": 80},
    "Water body change": {"water": 80},
    "Urban expansion / new construction": {"built-up": 50},
    "Deforestation / vegetation loss": {"tree cover": 10},
    "Likely bare soil / land clearing": {"bare/sparse vegetation": 60},
    "Agricultural land conversion": {"cropland": 40},
}

WORLDCOVER_NAMES: dict[int, str] = {
    10: "tree cover",
    20: "shrubland",
    30: "grassland",
    40: "cropland",
    50: "built-up",
    60: "bare/sparse vegetation",
    70: "snow and ice",
    80: "water",
    90: "wetland",
    95: "mangroves",
    100: "moss and lichen",
}

REPORT_NOTE = (
    "Agreement with a reference map is a sanity check, not a performance score. The "
    "reference map is a single-date snapshot while change detection compares two dates, "
    "and the two rasters may differ in resolution, date and definition. Patches whose "
    "change type has no single expected reference class are skipped."
)


def majority_class_in_box(class_map: np.ndarray, box: list[int]) -> int | None:
    """Most common class code inside a [x, y, width, height] pixel box."""
    x, y, width, height = (int(value) for value in box)
    rows, cols = class_map.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(cols, x + width), min(rows, y + height)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = class_map[y0:y1, x0:x1]
    if not crop.size:
        return None
    values, counts = np.unique(crop, return_counts=True)
    return int(values[int(np.argmax(counts))])


def build_agreement_report(
    regions: list[dict],
    class_map: np.ndarray,
    class_names: dict[int, str] | None = None,
) -> dict:
    """Compare each change patch against the reference map and summarise."""
    class_names = class_names or {}
    rows = []
    matched = 0
    skipped = 0
    for index, region in enumerate(regions, start=1):
        change_type = region.get("change_type") or ""
        expected = EXPECTED_CLASSES.get(change_type)
        box = region.get("bounding_box")
        if expected is None or not isinstance(box, list) or len(box) != 4:
            skipped += 1
            continue
        majority = majority_class_in_box(np.asarray(class_map), box)
        agreed = majority in expected.values()
        matched += int(agreed)
        if majority is None:
            name = "no data"
        else:
            name = class_names.get(majority, str(majority))
        rows.append(
            {
                "region_id": index,
                "change_type": change_type,
                "reference_majority_class": majority,
                "reference_class_name": name,
                "agrees": bool(agreed),
            }
        )
    total = len(rows)
    return {
        "reference_map": "user-provided land-cover map",
        "note": REPORT_NOTE,
        "rows": rows,
        "summary": {
            "patches_checked": total,
            "patches_agreeing": matched,
            "patches_skipped_no_expected_class": skipped,
            "agreement_percent": round(100.0 * matched / total, 2) if total else None,
        },
    }
