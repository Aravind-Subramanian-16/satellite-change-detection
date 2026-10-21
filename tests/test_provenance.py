from provenance import APP_VERSION, build_provenance, get_commit_hash, utc_timestamp


def test_provenance_contains_reproducibility_fields():
    data = build_provenance(
        "spectral",
        profile="general",
        thresholds={"ndvi_drop": -0.15},
        scene_ids=["S2A", "S2B"],
        dates={"before": "2024-01-01", "after": "2024-02-01"},
        percent_masked=12.5,
    )
    assert data["commit"] and data["commit"] != ""
    assert data["app_version"] == APP_VERSION
    assert data["pipeline"] == "spectral"
    assert data["profile"] == "general"
    assert data["scene_ids"] == ["S2A", "S2B"]
    assert data["percent_masked"] == 12.5
    assert data["timestamp_utc"].endswith("+00:00")


def test_commit_hash_and_timestamp_are_stable_strings():
    assert isinstance(get_commit_hash(), str)
    assert "T" in utc_timestamp()
