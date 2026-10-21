"""GeoJSON and CSV export of detected regions, with provenance and units."""
from __future__ import annotations

import csv
import io
import json


def _geometry_for(region: dict, aoi: dict | None, shape: list[int] | None) -> tuple[dict, dict]:
    x, y, width, height = [float(value) for value in region.get("bounding_box", [0, 0, 0, 0])]
    properties = {}
    if aoi and shape and aoi.get("bbox"):
        west, south, east, north = aoi["bbox"]
        image_height, image_width = shape[:2]
        if image_width and image_height:
            x = max(0.0, min(x, image_width))
            y = max(0.0, min(y, image_height))
            width = max(0.0, min(width, image_width - x))
            height = max(0.0, min(height, image_height - y))
            lon_left = west + (x / image_width) * (east - west)
            lon_right = west + ((x + width) / image_width) * (east - west)
            lat_top = north - (y / image_height) * (north - south)
            lat_bottom = north - ((y + height) / image_height) * (north - south)
            ring = [
                [lon_left, lat_bottom],
                [lon_right, lat_bottom],
                [lon_right, lat_top],
                [lon_left, lat_top],
                [lon_left, lat_bottom],
            ]
            properties = {
                "centroid_lon": round((lon_left + lon_right) / 2.0, 7),
                "centroid_lat": round((lat_top + lat_bottom) / 2.0, 7),
            }
            return {"type": "Polygon", "coordinates": [ring]}, properties
    ring = [[x, y], [x + width, y], [x + width, y + height], [x, y + height], [x, y]]
    return {"type": "Polygon", "coordinates": [ring]}, {"centroid_x": x + width / 2.0, "centroid_y": y + height / 2.0}


def regions_to_geojson(result: dict) -> dict:
    aoi = result.get("aoi")
    shape = result.get("image_shape")
    features = []
    for index, region in enumerate(result.get("change_regions") or [], start=1):
        geometry, centroid = _geometry_for(region, aoi, shape)
        properties = {
            "region_id": index,
            "change_type": region.get("change_type"),
            "confidence": region.get("confidence_label"),
            "pixel_area": region.get("pixel_area"),
            "area_m2": region.get("area_m2"),
            "area_ha": region.get("area_ha"),
            "uncertainty": region.get("uncertainty"),
            "explanation": region.get("explanation"),
            "profile": result.get("profile", "general"),
            **centroid,
        }
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    provenance = result.get("provenance") or {}
    metadata = {
        "coordinate_reference_system": "EPSG:4326" if aoi and shape else "image-pixel (origin top-left)",
        "pipeline": result.get("pipeline"),
        "profile": result.get("profile", "general"),
        "validation_status": result.get("validation_status"),
        "scene_ids": provenance.get("scene_ids"),
        "dates": provenance.get("dates"),
        "commit": provenance.get("commit"),
        "timestamp_utc": provenance.get("timestamp_utc"),
        "percent_masked": result.get("percent_cloud_masked"),
        "note": "Bounding-box polygons. Decision support, not ground truth.",
    }
    class_table = result.get("class_table")
    if class_table and class_table.get("rows"):
        metadata["class_table"] = class_table
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": metadata,
    }


def regions_to_csv(result: dict) -> str:
    buffer = io.StringIO()
    columns = [
        "region_id", "change_type", "confidence", "pixel_area", "area_m2", "area_ha",
        "uncertainty", "x", "y", "width", "height", "centroid_lon", "centroid_lat",
        "explanation",
    ]
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    aoi = result.get("aoi")
    shape = result.get("image_shape")
    for index, region in enumerate(result.get("change_regions") or [], start=1):
        _, centroid = _geometry_for(region, aoi, shape)
        x, y, width, height = region.get("bounding_box", [0, 0, 0, 0])
        writer.writerow(
            {
                "region_id": index,
                "change_type": region.get("change_type"),
                "confidence": region.get("confidence_label"),
                "pixel_area": region.get("pixel_area"),
                "area_m2": region.get("area_m2"),
                "area_ha": region.get("area_ha"),
                "uncertainty": region.get("uncertainty"),
                "x": x, "y": y, "width": width, "height": height,
                "centroid_lon": centroid.get("centroid_lon", ""),
                "centroid_lat": centroid.get("centroid_lat", ""),
                "explanation": region.get("explanation", ""),
            }
        )
    class_table = result.get("class_table")
    if class_table and class_table.get("rows"):
        summary_writer = csv.DictWriter(
            buffer,
            fieldnames=["class", "area_ha", "area_m2", "percent_of_aoi", "region_count"],
            lineterminator="\n",
        )
        buffer.write("\nclass_summary\n")
        summary_writer.writeheader()
        for row in class_table["rows"]:
            summary_writer.writerow(
                {
                    "class": row["change_type"],
                    "area_ha": row["area_ha"],
                    "area_m2": row["area_m2"],
                    "percent_of_aoi": row["percent_of_aoi"],
                    "region_count": row["region_count"],
                }
            )
        total = class_table.get("total") or {}
        summary_writer.writerow(
            {
                "class": total.get("change_type", "Total"),
                "area_ha": total.get("area_ha", ""),
                "area_m2": total.get("area_m2", ""),
                "percent_of_aoi": total.get("percent_of_aoi", ""),
                "region_count": total.get("region_count", ""),
            }
        )
        note = class_table.get("note")
        if note:
            buffer.write(f"# {note}\n")
    return buffer.getvalue()


def geojson_bytes(result: dict) -> bytes:
    return json.dumps(regions_to_geojson(result), indent=2).encode("utf-8")


def csv_bytes(result: dict) -> bytes:
    return regions_to_csv(result).encode("utf-8")
