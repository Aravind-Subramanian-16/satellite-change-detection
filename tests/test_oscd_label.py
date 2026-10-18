"""Unit tests for benchmarks/oscd_eval.py label loading."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks"))


rasterio = pytest.importorskip("rasterio", reason="rasterio required for OSCD label tests")


def _write_label_tif(directory: Path, city: str, data: np.ndarray) -> Path:
    """Write a single-band GeoTIFF label file in the OSCD layout."""
    label_dir = directory / city / "cm"
    label_dir.mkdir(parents=True, exist_ok=True)
    path = label_dir / f"{city}-cm.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
        count=1, dtype=data.dtype,
    ) as ds:
        ds.write(data, 1)
    return path


class TestLoadLabel:
    """Tests for oscd_eval.load_label."""

    def test_valid_binary_mask(self, tmp_path):
        """A label with values {1, 2} produces a boolean mask where 2 → True."""
        from oscd_eval import load_label

        data = np.array([[1, 2], [1, 1]], dtype=np.uint8)
        _write_label_tif(tmp_path, "testcity", data)

        mask, shape = load_label(tmp_path, "testcity")
        assert shape == (2, 2)
        assert mask.dtype == bool
        expected = np.array([[False, True], [False, False]])
        np.testing.assert_array_equal(mask, expected)

    def test_all_no_change(self, tmp_path):
        """A label with only value 1 (no change) is valid."""
        from oscd_eval import load_label

        data = np.ones((4, 4), dtype=np.uint8)
        _write_label_tif(tmp_path, "quiet", data)

        mask, _ = load_label(tmp_path, "quiet")
        assert not mask.any()

    def test_all_change(self, tmp_path):
        """A label with only value 2 (all change) is valid."""
        from oscd_eval import load_label

        data = np.full((3, 3), 2, dtype=np.uint8)
        _write_label_tif(tmp_path, "active", data)

        mask, _ = load_label(tmp_path, "active")
        assert mask.all()

    def test_invalid_values_raises(self, tmp_path):
        """Values outside {1, 2} must raise ValueError."""
        from oscd_eval import load_label

        data = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        _write_label_tif(tmp_path, "bad", data)

        with pytest.raises(ValueError, match="must contain only values"):
            load_label(tmp_path, "bad")

    def test_missing_file_raises(self, tmp_path):
        """A missing GeoTIFF must raise FileNotFoundError."""
        from oscd_eval import load_label

        with pytest.raises(FileNotFoundError, match="missing change label GeoTIFF"):
            load_label(tmp_path, "nonexistent")

    def test_mask_shape_matches_input(self, tmp_path):
        """Returned mask shape must match the raster dimensions."""
        from oscd_eval import load_label

        data = np.array([[1, 2, 1, 2, 1],
                         [2, 1, 2, 1, 2],
                         [1, 1, 1, 2, 2]], dtype=np.uint8)
        _write_label_tif(tmp_path, "shaped", data)

        mask, shape = load_label(tmp_path, "shaped")
        assert mask.shape == shape == (3, 5)

    def test_load_city_uses_tif_and_checks_band_dimensions(self, tmp_path):
        """The loader uses GeoTIFF labels, ignores cm.png, and rejects size mismatches."""
        from oscd_eval import BANDS, load_city

        city = "synthetic"
        label = np.array([[1, 2], [2, 1]], dtype=np.uint8)
        _write_label_tif(tmp_path / "labels", city, label)

        image_city = tmp_path / "images" / city
        for acquisition in ("imgs_1_rect", "imgs_2_rect"):
            directory = image_city / acquisition
            directory.mkdir(parents=True)
            for band in BANDS:
                with rasterio.open(
                    directory / f"{band}.tif", "w", driver="GTiff", height=2,
                    width=2, count=1, dtype="uint16",
                ) as ds:
                    ds.write(np.ones((2, 2), dtype=np.uint16), 1)
        # A contradictory visualization must have no effect on the ground truth.
        png_dir = tmp_path / "labels" / city / "cm"
        from PIL import Image
        Image.fromarray(np.full((2, 2, 3), 255, dtype=np.uint8)).save(png_dir / "cm.png")

        result = load_city(tmp_path / "images", tmp_path / "labels", city)
        np.testing.assert_array_equal(result["mask"], label == 2)

        # One mismatched imagery raster is reported, not resized.
        bad_band = image_city / "imgs_2_rect" / "B11.tif"
        bad_band.unlink()
        with rasterio.open(
            bad_band, "w", driver="GTiff", height=1, width=2, count=1, dtype="uint16",
        ) as ds:
            ds.write(np.ones((1, 2), dtype=np.uint16), 1)
        with pytest.raises(ValueError, match="raster/label dimensions differ.*refusing to resize"):
            load_city(tmp_path / "images", tmp_path / "labels", city)
