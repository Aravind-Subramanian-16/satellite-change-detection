"""Declarative analysis profiles layered on the existing spectral pipeline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REGISTRY_PATH = Path(__file__).with_name("validation_status.json")


@dataclass(frozen=True)
class ProfileConfig:
    key: str
    label: str
    description: str
    indices: tuple[str, ...]
    thresholds: dict
    mmu_ha: float = 0.0
    season_warning: bool = True
    vegetated_before_ndvi: float | None = None
    cloud_mask_mandatory: bool = False
    supports_timeline: bool = False
    show_road_context: bool = False
    report_wording: tuple[str, ...] = ()
    honesty_notes: tuple[str, ...] = ()
    threshold_provenance: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


PROFILES: dict[str, ProfileConfig] = {
    "general": ProfileConfig(
        key="general",
        label="General change (default)",
        description="NDVI decrease or NDBI increase; the original application behaviour, unchanged.",
        indices=("ndvi", "ndbi"),
        thresholds={"ndvi_drop": -0.15, "ndbi_rise": 0.10},
        mmu_ha=0.0,
        season_warning=True,
        report_wording=(
            "Generic spectral difference. Change types are heuristic colour/index rules, not a land-cover classifier.",
        ),
        honesty_notes=(
            "Decision support, not ground truth. Verify every region against imagery and local knowledge.",
            "Single-pair differences can be caused by season, moisture, haze or sensor geometry.",
        ),
    ),
    "agriculture": ProfileConfig(
        key="agriculture",
        label="Agriculture",
        description="NDVI and NDMI (B08/B11) difference for cropland stress, vegetation loss or gain.",
        indices=("ndvi", "ndmi"),
        thresholds={"ndvi_drop": 0.15, "ndmi_drop": 0.12, "stress_ndvi_drop": 0.05, "ndvi_gain": 0.15},
        mmu_ha=0.5,
        season_warning=True,
        supports_timeline=True,
        report_wording=(
            "A single NDVI/NDMI pair confuses harvest, irrigation scheduling and seasonal phenology with crop damage.",
            "Use the multi-date NDVI timeline and field knowledge before interpreting a loss as stress.",
            "Patches that became greener are reported separately from patches that lost greenness.",
        ),
        honesty_notes=(
            "Unvalidated, qualitative only: no labelled agriculture dataset has been scored.",
            "At 10 m, small fields, mixed crops and field boundaries are sub-pixel or mixed.",
            "A same-season pair is required for interpretation; cross-season results are flagged.",
        ),
        threshold_provenance={
            "ndvi_drop": "pre-existing threshold, unchanged in this redesign.",
            "ndmi_drop": "pre-existing threshold, unchanged in this redesign.",
            "stress_ndvi_drop": "pre-existing threshold, unchanged in this redesign.",
            "ndvi_gain": "chosen by developer, untested: mirrors the magnitude of ndvi_drop so greening and browning are treated symmetrically.",
        },
    ),
    "deforestation": ProfileConfig(
        key="deforestation",
        label="Deforestation",
        description="NBR (B08/B12) and NDVI drop restricted to pixels vegetated in the before image.",
        indices=("ndvi", "nbr"),
        thresholds={"nbr_drop": 0.10, "ndvi_drop": 0.15},
        mmu_ha=0.5,
        season_warning=True,
        vegetated_before_ndvi=0.30,
        cloud_mask_mandatory=True,
        report_wording=(
            "Only pixels with before-NDVI at or above the vegetated threshold are eligible; the minimum mapping unit removes speckle.",
            "This is not a forest inventory and does not distinguish selective logging from clear-cut or fire.",
        ),
        honesty_notes=(
            "Unvalidated, qualitative only: no labelled forest-loss dataset has been scored.",
            "Cloud and shadow masking is mandatory; masked area is excluded, not inferred.",
            "A 0.5 ha MMU at 10 m is about 50 pixels; smaller losses are intentionally discarded.",
        ),
    ),
    "builtup": ProfileConfig(
        key="builtup",
        label="Built-up / industrial",
        description="NDBI, bare-soil index and NDVI-loss cue; the reasoner separates construction from cleared land.",
        indices=("ndvi", "ndbi", "bsi"),
        thresholds={"ndbi_rise": 0.10, "bsi_rise": 0.05, "ndvi_drop": 0.10},
        mmu_ha=0.25,
        season_warning=True,
        report_wording=(
            "Urban change is the only label family covered by the OSCD benchmark; other construction types remain unvalidated.",
            "New construction versus cleared land is a deterministic heuristic, not a learned classifier.",
        ),
        honesty_notes=(
            "Quantitatively benchmarked on OSCD (urban change only, pooled F1 about 0.12); verify the v2 result file before quoting.",
            "The profile's extra NDBI/BSI cues and MMU are not separately ablated against OSCD here.",
            "Industrial roofs, bare soil and roads can share spectral signatures at 10 m.",
        ),
    ),
    "roads": ProfileConfig(
        key="roads",
        label="Roads / infrastructure (context only)",
        description="No road detection claim. Reports changed area within a distance of mapped OpenStreetMap roads.",
        indices=("ndvi", "ndbi"),
        thresholds={"ndvi_drop": -0.15, "ndbi_rise": 0.10},
        mmu_ha=0.0,
        show_road_context=True,
        report_wording=(
            "Roads narrower than about 20 m are mostly sub-pixel at 10 m Sentinel-2 resolution; this profile does not detect roads.",
            "OpenStreetMap is used as context only. ODbL licence obligations must be verified before redistribution.",
        ),
        honesty_notes=(
            "Unvalidated, qualitative only; there is no road ground truth here.",
            "The road context depends on OSM completeness and positional accuracy, which vary by region.",
            "Changed area near a mapped road is not evidence that the road itself changed.",
        ),
    ),
    "water": ProfileConfig(
        key="water",
        label="Water",
        description="NDVI and NDMI (moisture) rules for open water appearing or disappearing. The green band needed for the usual water index is not fetched, so this is a coarse estimate.",
        indices=("ndvi", "ndmi"),
        thresholds={"water_ndvi_max": -0.05, "water_ndmi_max": -0.15},
        mmu_ha=0.25,
        season_warning=True,
        cloud_mask_mandatory=True,
        report_wording=(
            "Water is estimated from two moisture-sensitive indices (NDVI and NDMI). Wet soil, shadow and dark surfaces can be confused with open water.",
            "Cloud and shadow masking is mandatory for this profile because shadows look like water.",
            "Patches are labelled 'New surface water' or 'Water lost' by comparing the before and after indices.",
        ),
        honesty_notes=(
            "Unvalidated, qualitative only: no labelled water dataset has been scored.",
            "Seasonal floods, tides, irrigation and reservoir operation change water extent between any two dates; this is not a flood assessment.",
            "A 0.25 ha minimum mapping unit at 10 m is about 25 pixels; smaller ponds are intentionally discarded.",
        ),
        threshold_provenance={
            "water_ndvi_max": "chosen by developer, untested: open water typically has NDVI below 0; -0.05 admits mixed shoreline pixels.",
            "water_ndmi_max": "chosen by developer, untested: NDMI (B08/B11 moisture index) is negative over open water; -0.15 requires a clear moisture signal.",
        },
    ),
}


def load_validation_status() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def get_profile(key: str | None) -> ProfileConfig:
    key = (key or "general").strip().lower()
    if key not in PROFILES:
        raise ValueError(f"Unknown analysis profile '{key}'. Choose one of: {', '.join(PROFILES)}")
    return PROFILES[key]


def profile_public(key: str | None) -> dict:
    config = get_profile(key)
    registry = load_validation_status().get(config.key, {})
    return {
        "key": config.key,
        "label": config.label,
        "description": config.description,
        "indices": list(config.indices),
        "thresholds": dict(config.thresholds),
        "default_mmu_ha": config.mmu_ha,
        "vegetated_before_ndvi": config.vegetated_before_ndvi,
        "cloud_mask_mandatory": config.cloud_mask_mandatory,
        "supports_timeline": config.supports_timeline,
        "show_road_context": config.show_road_context,
        "report_wording": list(config.report_wording),
        "honesty_notes": list(config.honesty_notes),
        "threshold_provenance": dict(config.threshold_provenance),
        "validation_status": registry.get("status", "unvalidated, qualitative only"),
        "validation_short": registry.get("short", "unvalidated"),
        "validation_evidence": registry.get("evidence", ""),
        "display_metrics": bool(registry.get("display_metrics", False)),
    }


def all_profiles_public() -> list[dict]:
    return [profile_public(key) for key in PROFILES]
