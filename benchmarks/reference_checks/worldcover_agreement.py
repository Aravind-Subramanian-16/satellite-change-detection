#!/usr/bin/env python
"""Compare a saved change-detection result against a land-cover GeoTIFF.

Example
-------
    python worldcover_agreement.py \
        --result analysis-result.json \
        --reference ESA_WorldCover_10m_2021_v200_Map.tif \
        --out agreement-report.json

The result JSON must contain ``change_regions``, ``image_shape`` and
``aoi.bbox`` (exactly what the app's /fetch-and-predict response includes;
the GeoJSON export is not enough because it carries no AOI bbox).

The reference raster is reprojected and resampled to the analysis grid, then
compared patch by patch. Output is labelled "agreement with a reference map"
— it is not an accuracy score; see benchmarks/reference_checks/README.md.

Downloading
-----------
Use ``--download URL`` to fetch a reference tile. The script prints the
remote file size first and asks for confirmation before downloading
anything, so you always see how much data you are about to pull.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agreement import WORLDCOVER_NAMES, build_agreement_report  # noqa: E402


def _load_result(path: str) -> dict:
    with open(path) as handle:
        return json.load(handle)


def _validate_result(result: dict) -> None:
    for key in ("change_regions", "image_shape", "aoi"):
        if key not in result:
            raise SystemExit(
                f"The result file is missing '{key}'. Save the full /fetch-and-predict "
                "response (history export has it) rather than the GeoJSON export."
            )
    if not result["aoi"].get("bbox"):
        raise SystemExit("The result has no aoi.bbox; pixel boxes cannot be placed geographically.")


def _align_reference(reference: str, result: dict) -> "numpy.ndarray":  # noqa: F821
    try:
        import numpy as np
        import rasterio
        from rasterio.warp import calculate_default_transform, reproject, Resampling
        from rasterio.crs import CRS
        from rasterio.transform import from_bounds
    except ImportError as exc:
        raise SystemExit(
            "rasterio is needed to align the reference GeoTIFF (pip install rasterio). "
            "The app itself does not depend on it."
        ) from exc

    west, south, east, north = result["aoi"]["bbox"]
    height, width = result["image_shape"][:2]
    dst_crs = CRS.from_epsg(4326)
    dst_transform = from_bounds(west, south, east, north, width, height)
    destination = np.zeros((height, width), dtype=np.uint8)
    try:
        with rasterio.open(reference) as src:
            transform, _, _ = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds, dst_width=width, dst_height=height
            )
            reproject(
                source=rasterio.band(src, 1),
                destination=destination,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.mode,
            )
    except Exception as exc:
        raise SystemExit(f"Could not read or align the reference raster: {exc}") from exc
    return destination


def _remote_size(url: str) -> int:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "scd-reference-check"})
    with urllib.request.urlopen(request, timeout=30) as response:
        size = response.headers.get("Content-Length")
        return int(size) if size else 0


def _download(url: str, destination: str) -> None:
    size = _remote_size(url)
    size_text = f"{size / (1024 * 1024):.1f} MB" if size else "unknown size"
    answer = input(f"Download {size_text} from {url} to {destination}? [y/N] ").strip().lower()
    if answer != "y":
        raise SystemExit("Download cancelled.")
    urllib.request.urlretrieve(url, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--result", required=True, help="saved /fetch-and-predict response JSON")
    parser.add_argument("--reference", help="land-cover GeoTIFF aligned by this script")
    parser.add_argument("--download", help="URL of a land-cover tile to fetch first (size is shown and confirmed)")
    parser.add_argument("--out", required=True, help="output JSON path for the agreement report")
    args = parser.parse_args()

    if args.download:
        _download(args.download, args.reference or "reference.tif")
    if not args.reference:
        raise SystemExit("--reference is required when not downloading.")

    result = _load_result(args.result)
    _validate_result(result)
    class_map = _align_reference(args.reference, result)
    report = build_agreement_report(result["change_regions"], class_map, class_names=WORLDCOVER_NAMES)
    report["reference_map"] = args.reference
    with open(args.out, "w") as handle:
        json.dump(report, handle, indent=2)
    summary = report["summary"]
    print(
        f"{summary['patches_agreeing']} of {summary['patches_checked']} checked patches "
        f"agree with the reference map ({summary['agreement_percent']}%); "
        f"{summary['patches_skipped_no_expected_class']} skipped (no expected class)."
    )
    print(f"Report written to {args.out}. This is agreement with a reference map, not a performance score.")


if __name__ == "__main__":
    main()
