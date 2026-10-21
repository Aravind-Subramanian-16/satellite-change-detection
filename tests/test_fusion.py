import numpy as np
import pytest

from fusion import (
    FusionConfig,
    fuse_scores,
    fusion_from_indices,
    robust_normalise,
    select_fusion_config,
    spectral_evidence,
)


def test_robust_normalise_and_spectral_evidence():
    values = np.array([0.0, 0.0, 0.0, 0.0, 1.0, 2.0], dtype=np.float32)
    normalised = robust_normalise(values)
    assert normalised.min() >= 0.0 and normalised.max() <= 1.0
    assert robust_normalise(np.zeros((4, 4))).sum() == 0

    ndvi_a = np.array([[0.7, 0.6]], dtype=np.float32)
    ndbi_a = np.array([[0.1, 0.2]], dtype=np.float32)
    ndvi_b = np.array([[0.2, 0.6]], dtype=np.float32)
    ndbi_b = np.array([[0.1, 0.5]], dtype=np.float32)
    evidence = spectral_evidence(ndvi_a, ndbi_a, ndvi_b, ndbi_b)
    assert evidence[0, 0] == pytest.approx(0.5)
    assert evidence[0, 1] == pytest.approx(0.3)


def test_fusion_endpoints_and_validation():
    spectral = np.zeros((4, 4), dtype=np.float32)
    learned = np.zeros((4, 4), dtype=np.float32)
    learned[0, :] = 1.0
    fused, mask, meta = fuse_scores(spectral, learned, FusionConfig(spectral_weight=0.0, threshold=0.5))
    assert mask[0].all() and not mask[1:].any()
    assert meta["learned_weight"] == 1.0
    assert fused.max() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="share one shape"):
        fuse_scores(np.zeros((2, 2)), np.zeros((3, 3)))
    with pytest.raises(ValueError, match="within"):
        FusionConfig(spectral_weight=1.5)


def test_fusion_recovers_complementary_changes_and_selection_beats_single_models():
    labels = np.zeros((20, 20), dtype=bool)
    labels[2:6, 2:6] = True
    labels[12:16, 12:16] = True
    spectral = np.zeros((20, 20), dtype=np.float32)
    spectral[2:6, 2:6] = 1.0
    learned = np.zeros((20, 20), dtype=np.float32)
    learned[12:16, 12:16] = 0.9
    config, rows = select_fusion_config(spectral, learned, labels, weights=(0.0, 0.5, 1.0))
    assert rows
    best = max(rows, key=lambda row: row["f1"])
    assert best["f1"] >= 0.99
    assert config.spectral_weight == pytest.approx(0.5)
    _, fused_mask, _ = fuse_scores(spectral, learned, config)
    assert fused_mask.sum() == labels.sum()


def test_fusion_from_indices_runs_without_cloud_mask():
    before = {"ndvi": np.full((6, 6), 0.7), "ndbi": np.full((6, 6), 0.0)}
    after = {"ndvi": np.full((6, 6), 0.2), "ndbi": np.full((6, 6), 0.4)}
    fused, mask, meta = fusion_from_indices(before, after, np.full((6, 6), 0.8), FusionConfig(threshold=0.4))
    assert fused.shape == (6, 6)
    assert mask.all()
    assert meta["method"] == "weighted_probability_fusion"
