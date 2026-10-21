"""Synthetic-data tests for the submission-paper figures and tables."""
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.oscd_eval import OFFICIAL_TEST_CITIES  # noqa: E402
from benchmarks.oscd_evidence import compute_metrics, load_results  # noqa: E402
from scripts.make_paper_figures import (  # noqa: E402
    city_f1_intervals,
    load_degradation_csv,
    make_all_figures,
    pooled_from_rows,
)

METHOD_ROWS = {
    "hardcoded": ("spectral", "hardcoded", None, (10, 5, 20, 965)),
    "percentile": ("spectral", "percentile", None, (15, 10, 15, 960)),
    "otsu": ("spectral", "otsu", None, (30, 500, 0, 470)),
    "cnn_joint": ("cnn", "pipeline_a_cnn_joint_percentile_chosen_on_train", "joint_percentile", (0, 0, 30, 970)),
    "cnn_reflectance": ("cnn", "pipeline_a_cnn_reflectance_other", "reflectance", (0, 0, 30, 970)),
}


def _row(city: str, method: str) -> dict:
    pipeline, configuration, preprocess, counts = METHOD_ROWS[method]
    values = compute_metrics(*counts)
    row = {
        "city": city,
        "pipeline": pipeline,
        "configuration": configuration,
        "split": "test",
        "metrics": values,
        "predicted_fraction": values["predicted_fraction"],
        "true_fraction": values["true_fraction"],
    }
    if preprocess:
        row["preprocess"] = preprocess
        row["selection"] = "chosen on train" if method == "cnn_joint" else "other"
    return row


def _fake_results(tmp_path: Path) -> tuple[Path, list[dict]]:
    rows = [_row(city, method) for city in OFFICIAL_TEST_CITIES for method in METHOD_ROWS]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(rows))
    return path, rows


def _fake_degradation(tmp_path: Path) -> Path:
    path = tmp_path / "degradation.csv"
    rows = []
    for factor, resolution in ((1, "0.5m"), (2, "1.0m"), (4, "2.0m"), (8, "4.0m"), (16, "8.0m"), (20, "10.0m")):
        for image, (tp, fp, fn) in (("a.png", (10, 10, 10)), ("b.png", (30, 0, 0))):
            rows.append(
                {
                    "image": image,
                    "factor": factor,
                    "real_world_resolution": resolution,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                }
            )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["image", "factor", "real_world_resolution", "tp", "fp", "fn"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_figures_tables_and_manifest_are_generated_from_saved_data(tmp_path):
    source, rows = _fake_results(tmp_path)
    degradation = _fake_degradation(tmp_path)
    before = source.read_bytes()
    manifest = make_all_figures(source, tmp_path / "out", degradation_csv=degradation, resamples=200)

    assert source.read_bytes() == before
    assert manifest["rows"] == len(rows) == 50
    assert manifest["cities"] == sorted(OFFICIAL_TEST_CITIES)
    assert manifest["methods"][0] == "hardcoded"
    assert manifest["results_sha256"]
    assert manifest["degradation"]["available"] is True
    assert manifest["degradation"]["n_images"] == 2
    assert manifest["intervals"]["per_city_resamples"] == 200
    for name in manifest["figures"].values():
        assert (tmp_path / "out" / name).stat().st_size > 1000
    degradation_table = (tmp_path / "out" / "generated_degradation_table.tex").read_text()
    assert "80.00" in degradation_table and "66.67" in degradation_table
    assert "2 LEVIR-CD" in degradation_table
    oscd_table = (tmp_path / "out" / "generated_oscd_table.tex").read_text()
    assert "Hardcoded NDVI/NDBI" in oscd_table
    assert "Random at prevalence" in oscd_table
    assert "All no change" in oscd_table
    assert "0.4444" in oscd_table
    assert "OA" in oscd_table and "0.9750" in oscd_table


def test_pooled_metrics_use_confusion_totals_not_city_averages(tmp_path):
    by_method = load_results(_fake_results(tmp_path)[0], expected_cities=OFFICIAL_TEST_CITIES)
    pooled = pooled_from_rows(by_method["hardcoded"])
    assert pooled["tp"] == 100
    assert pooled["fp"] == 50
    assert pooled["fn"] == 200
    assert pooled["tn"] == 9650
    assert pooled["precision"] == pytest.approx(100 / 150)
    assert pooled["recall"] == pytest.approx(100 / 300)
    assert pooled["f1"] == pytest.approx(2 * (2 / 3) * (1 / 3) / (2 / 3 + 1 / 3))
    assert pooled["true_fraction"] == pytest.approx(300 / 10_000)


def test_degradation_loader_pools_counts_instead_of_averaging_per_image(tmp_path):
    data = load_degradation_csv(_fake_degradation(tmp_path))
    assert data["n_images"] == 2
    assert data["factors"] == (1, 2, 4, 8, 16, 20)
    assert data["metrics"][1]["tp"] == 40
    assert data["metrics"][1]["fp"] == 10
    assert data["metrics"][1]["fn"] == 10
    assert data["metrics"][1]["f1"] == pytest.approx(0.8)
    assert data["metrics"][1]["iou"] == pytest.approx(40 / 60)
    assert data["metrics"][1]["predicted_pixels"] == 50
    assert data["metrics"][1]["f1"] != pytest.approx((0.5 + 1.0) / 2)


def test_degradation_loader_rejects_incomplete_image_coverage(tmp_path):
    path = _fake_degradation(tmp_path)
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if not (row["image"] == "b.png" and row["factor"] == "20")]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["image", "factor", "real_world_resolution", "tp", "fp", "fn"])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="same images"):
        load_degradation_csv(path)


def test_missing_degradation_source_is_a_labelled_placeholder(tmp_path):
    source, _ = _fake_results(tmp_path)
    manifest = make_all_figures(source, tmp_path / "out", degradation_csv=tmp_path / "absent.csv", resamples=100)
    assert manifest["degradation"]["available"] is False
    assert "placeholder" in manifest["figures"]["resolution_f1"]
    assert (tmp_path / "out" / manifest["figures"]["resolution_f1"]).stat().st_size > 1000
    table = (tmp_path / "out" / "generated_degradation_table.tex").read_text()
    assert "Source data not found" in table
    assert "80.00" not in table


def test_city_intervals_are_deterministic_bounded_and_zero_for_empty_prediction(tmp_path):
    by_method = load_results(_fake_results(tmp_path)[0], expected_cities=OFFICIAL_TEST_CITIES)
    first = city_f1_intervals(by_method, seed=0, resamples=200)
    second = city_f1_intervals(by_method, seed=0, resamples=200)
    assert first == second
    for method, values in first.items():
        for city, estimate in values.items():
            assert estimate["point"] == pytest.approx(by_method[method][city]["metrics"]["f1"])
            low, high = estimate["ci95"]
            assert 0.0 <= low <= high <= 1.0
    assert first["cnn_reflectance"]["brasilia"]["ci95"] == [0.0, 0.0]


def test_generated_figures_are_greyscale_at_column_width(tmp_path):
    source, _ = _fake_results(tmp_path)
    manifest = make_all_figures(
        source,
        tmp_path / "out",
        degradation_csv=_fake_degradation(tmp_path),
        resamples=100,
    )
    for name in manifest["figures"].values():
        path = tmp_path / "out" / name
        pixels = np.asarray(Image.open(path).convert("RGB")).astype(int)
        assert np.abs(pixels[..., 0] - pixels[..., 1]).max() <= 2
        assert np.abs(pixels[..., 1] - pixels[..., 2]).max() <= 2
        width_inches = pixels.shape[1] / 300
        assert width_inches <= 3.6 or name == "fig_oscd_per_city_and_fractions.png"
