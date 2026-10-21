"""Compact plain-language explanations of why each changed patch was labelled.

These strings accompany region records in the API response, GeoJSON export and
results dashboard. They state the index/rule evidence behind a label so a
non-expert can check whether the reasoning fits what they see in the imagery.
"""

from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "New surface water": (
        "The after image is dark, and its vegetation index (NDVI {ndvi_after}) and moisture "
        "index (NDMI) sit below zero in this patch — typical of open water. The same patch was "
        "not water-like in the before image."
    ),
    "Water lost": (
        "The before image was water-like here (vegetation index NDVI {ndvi_before} below zero), "
        "and the after image is not. We flag the patch as surface water that disappeared."
    ),
    "Water body change": (
        "This patch is dark and water-like in the after image (NDVI {ndvi_after} below zero). "
        "Shadows can look similar, so treat this as an estimate."
    ),
    "Deforestation / vegetation loss": (
        "The vegetation index (NDVI) in this patch fell from {ndvi_before} to {ndvi_after}, and "
        "the patch was clearly vegetated before. That points to trees or dense vegetation being "
        "removed, though drought and harvest can look similar."
    ),
    "Agricultural land conversion": (
        "The patch switched between greener and less green states while staying partly vegetated, "
        "which is typical of farmland management between two dates."
    ),
    "Urban expansion / new construction": (
        "The built-up index (NDBI) rose while vegetation fell, and the patch looks uniform and "
        "grey in the after image — typical of new buildings, roads or paved ground. Cleared land "
        "can look similar early on."
    ),
    "Vegetation gain / reforestation": (
        "The vegetation index (NDVI) rose from {ndvi_before} to {ndvi_after}, so this patch "
        "became greener between the dates. Growth, planting or a wetter season can all cause this."
    ),
    "Likely bare soil / land clearing": (
        "The after image is warm-toned, bare-looking and not green, which is typical of exposed "
        "soil or clearing. On farmland this is often harvest or ploughing rather than damage."
    ),
    "Possible cloud interference": (
        "The patch is very bright and uniform, which can be cloud or haze rather than real "
        "change. Treat this patch as uncertain and check the before/after images."
    ),
    "Change detected (type unclear)": (
        "The images differ in this patch, but no rule agreed on a cause, so the type stays "
        "unclear. Check the before/after images yourself."
    ),
}


def _fmt(value) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "unknown"


def explain_region(region: dict, profile_key: str) -> str:
    """Return one or two plain sentences explaining the region's label."""
    change_type = region.get("change_type") or "Change detected (type unclear)"
    stats = region.get("stats") or {}
    template = TEMPLATES.get(change_type)
    if template is None:
        return "The images differ in this patch, but no rule agreed on a cause."
    return template.format(
        ndvi_before=_fmt(stats.get("ndvi_before")),
        ndvi_after=_fmt(stats.get("ndvi_after")),
    )
