import json

import pytest

from scripts.make_paper_figures import load_results, make_all_figures, method_key, pooled_metrics


def _row(city, method):
    configurations = {
        "hardcoded": ("spectral", "hardcoded", None),
        "percentile": ("spectral", "percentile", None),
        "otsu": ("spectral", "otsu", None),
        "cnn_joint": ("cnn", "pipeline_a_cnn_joint_percentile_chosen_on_train", "joint_percentile"),
        "cnn_reflectance": ("cnn", "pipeline_a_cnn_reflectance_other", "reflectance"),
    }
    pipeline, configuration, preprocess = configurations[method]
    row = {
        "city": city,
        "pipeline": pipeline,
        "configuration": configuration,
        "split": "test",
        "metrics": {
            "precision": 10 / 15,
            "recall": 10 / 25,
            "f1": 0.5,
            "iou": 1 / 3,
            "overall_accuracy": 0.8,
            "predicted_fraction": 0.15,
            "true_fraction": 0.25,
            "tp": 10,
            "fp": 5,
            "fn": 15,
            "tn": 70,
        },
    }
    if preprocess:
        row["preprocess"] = preprocess
        row["selection"] = "chosen on train" if method == "cnn_joint" else "other"
    return row


def _fake_results(tmp_path):
    rows = [
        _row(city, method)
        for city in ("alpha", "beta")
        for method in ("hardcoded", "percentile", "otsu", "cnn_joint", "cnn_reflectance")
    ]
    path = tmp_path / "results.json"
    path.write_text(json.dumps(rows))
    return path, rows


def test_figures_tables_and_manifest_are_generated_without_network(tmp_path):
    source, rows = _fake_results(tmp_path)
    before = source.read_bytes()
    manifest = make_all_figures(source, tmp_path / "out")

    assert source.read_bytes() == before
    assert manifest["rows"] == len(rows) == 10
    assert manifest["cities"] == ["alpha", "beta"]
    assert manifest["methods"][0] == "hardcoded"
    assert manifest["results_sha256"]
    for name in manifest["figures"].values():
        assert (tmp_path / "out" / name).stat().st_size > 1000
    pooled = (tmp_path / "out" / "generated_results_table.tex").read_text()
    assert "0.5000" in pooled
    assert "Spectral Otsu" in pooled
    per_city = (tmp_path / "out" / "generated_per_city_table.tex").read_text()
    assert "alpha" in per_city and "beta" in per_city
    assert per_city.count("\\\\") >= 10
    ablation = (tmp_path / "out" / "generated_ablation_table.tex").read_text()
    assert "not run" in ablation.lower()
    assert "fig_qualitative_placeholder.png" in manifest["figures"].values()


def test_pooled_metrics_use_confusion_totals():
    rows = [
        _row(city, method)
        for city in ("alpha", "beta")
        for method in ("hardcoded", "percentile", "otsu", "cnn_joint", "cnn_reflectance")
    ]
    metrics = pooled_metrics(rows)
    assert metrics["n_pixels"] == 1000
    assert metrics["precision"] == pytest.approx(20 / 30)
    assert metrics["recall"] == pytest.approx(20 / 50)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["overall_accuracy"] == pytest.approx(0.8)
    assert metrics["true_fraction"] == pytest.approx(0.25)


def test_loader_rejects_missing_methods_duplicates_and_non_test_rows(tmp_path):
    source, rows = _fake_results(tmp_path)
    incomplete = [row for row in rows if not (row["city"] == "alpha" and row["pipeline"] == "cnn")]
    source.write_text(json.dumps(incomplete))
    with pytest.raises(ValueError, match="missing methods"):
        load_results(source)

    source, rows = _fake_results(tmp_path)
    source.write_text(json.dumps(rows + [rows[0]]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_results(source)

    source, rows = _fake_results(tmp_path)
    rows[0]["split"] = "train"
    source.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="test results only"):
        load_results(source)


def test_method_identity_is_strict():
    assert method_key({"pipeline": "spectral", "configuration": "hardcoded"}) == "hardcoded"
    assert method_key({"pipeline": "cnn", "preprocess": "reflectance"}) == "cnn_reflectance"
    with pytest.raises(ValueError, match="Unknown CNN"):
        method_key({"pipeline": "cnn", "preprocess": "mystery"})
    with pytest.raises(ValueError, match="Unknown pipeline"):
        method_key({"pipeline": "magic", "configuration": "hardcoded"})


def test_optional_ablation_and_calibration_inputs_are_recorded(tmp_path):
    source, _ = _fake_results(tmp_path)
    ablation = tmp_path / "auto_improve_log.json"
    ablation.write_text(
        json.dumps(
            {
                "ablations": [
                    {
                        "component": "pif",
                        "pairs_available": 12,
                        "pairs_expected": 12,
                        "mean_delta_f1": 0.01,
                        "std_delta_f1": 0.02,
                        "decision": "kept",
                    }
                ]
            }
        )
    )
    calibration = tmp_path / "calibration.json"
    calibration.write_text(
        json.dumps(
            {
                "ece": 0.1,
                "bins": [
                    {"count": 10, "mean_confidence": 0.2, "accuracy": 0.1},
                    {"count": 0, "mean_confidence": None, "accuracy": None},
                ],
            }
        )
    )
    manifest = make_all_figures(source, tmp_path / "out", ablation_log=ablation, calibration_path=calibration)
    assert manifest["optional_inputs"]["ablation_log"]["available"] is True
    assert manifest["optional_inputs"]["calibration"]["available"] is True
    table = (tmp_path / "out" / "generated_ablation_table.tex").read_text()
    assert "pif" in table and "kept" in table
