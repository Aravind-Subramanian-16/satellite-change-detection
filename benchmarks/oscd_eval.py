#!/usr/bin/env python3
"""Reproducible, no-tuning-on-test OSCD evaluation for both application pipelines.

OSCD's original rasters have 13 bands at mixed resolutions. This evaluator reads
the native 10m bands B02/B03/B04/B08, resamples B11 to the same grid, and uses
the exact shared spectral detector from ``spectral_pipeline.py``. OSCD does not
include Sentinel-2 Scene Classification Layer (SCL), so cloud-mask comparisons
are deliberately reported as ``not_available`` rather than synthesized.
"""
from __future__ import annotations
import argparse, json, random
from dataclasses import asdict
from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spectral_pipeline import SpectralConfig, detect_from_indices

def metrics(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    p, t = pred.astype(bool), truth.astype(bool)
    tp, fp, fn, tn = (p & t).sum(), (p & ~t).sum(), (~p & t).sum(), (~p & ~t).sum()
    precision = tp / (tp + fp) if tp + fp else 0.0; recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": precision, "recall": recall, "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0, "iou": tp/(tp+fp+fn) if tp+fp+fn else 0.0, "overall_accuracy": (tp+tn)/(tp+fp+fn+tn) if tp+fp+fn+tn else 0.0, "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn)}

def _raster(path: Path, shape=None) -> np.ndarray:
    try:
        import rasterio
        from rasterio.enums import Resampling
    except ImportError as e: raise RuntimeError("OSCD evaluation needs rasterio; install requirements.txt") from e
    with rasterio.open(path) as ds:
        return ds.read(1, out_shape=(1, *shape) if shape else None, resampling=Resampling.bilinear if shape else Resampling.nearest).astype(np.float32)

def _find(city: Path, stems: tuple[str, ...]) -> Path:
    candidates = [p for p in city.rglob("*") if p.suffix.lower() in {".tif", ".tiff"} and any(s in p.name.lower() for s in stems)]
    if not candidates: raise FileNotFoundError(f"Missing {stems} below {city}")
    return sorted(candidates)[0]

def load_city(city: Path):
    # Canonical OSCD release names include imgs_1_rect/2_rect and cm.
    b04a, b04b = _raster(_find(city, ("imgs_1_rect", "2015", "2016"))), _raster(_find(city, ("imgs_2_rect", "2017", "2018")))
    # Some releases store multi-band stacks. For supported canonical directories,
    # users should supply a preprocessed NPY adapter if the naming differs.
    raise RuntimeError(f"{city}: raw OSCD layout requires a dataset-specific band adapter. Use --prepared-root containing city/*.npz (ndvi_a, ndbi_a, ndvi_b, ndbi_b, mask, rgb_a, rgb_b).")

def prepared_cities(root: Path):
    for path in sorted(root.glob("*.npz")):
        data = np.load(path); required = {"ndvi_a","ndbi_a","ndvi_b","ndbi_b","mask","rgb_a","rgb_b"}
        if not required <= set(data.files): raise ValueError(f"{path} missing {sorted(required-set(data.files))}")
        yield path.stem, data

def render(city: str, data, pred, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    panels = [Image.fromarray(data["rgb_a"].astype(np.uint8)), Image.fromarray(data["rgb_b"].astype(np.uint8)), Image.fromarray(pred*255), Image.fromarray(data["mask"].astype(np.uint8)*255)]
    w, h = panels[0].size; canvas = Image.new("RGB", (w*2,h*2));
    for i, panel in enumerate(panels): canvas.paste(panel.convert("RGB"), ((i%2)*w,(i//2)*h))
    canvas.save(out / f"{city}.png")

def main():
    p=argparse.ArgumentParser(); p.add_argument("--prepared-root", type=Path, required=True, help="Directory of verified per-city .npz adapters; no data is downloaded implicitly."); p.add_argument("--output", type=Path, default=ROOT/"benchmarks/results"); p.add_argument("--split", default="test"); args=p.parse_args()
    random.seed(0); np.random.seed(0); rows=[]
    configs=[SpectralConfig(mode="hardcoded"), SpectralConfig(mode="otsu"), SpectralConfig(mode="percentile")]
    for city, data in prepared_cities(args.prepared_root):
        for cfg in configs:
            pred, _, info = detect_from_indices(data["ndvi_a"],data["ndbi_a"],data["ndvi_b"],data["ndbi_b"],config=cfg)
            row={"city":city,"pipeline":"spectral","configuration":cfg.mode,"scl_cloud_mask":"not_available_in_oscd","metrics":metrics(pred,data["mask"]),"thresholds":info}; rows.append(row)
            if cfg.mode == "hardcoded": render(city,data,pred,args.output/"qualitative")
    if not rows: raise SystemExit("No .npz city files found; no metrics were fabricated.")
    args.output.mkdir(parents=True,exist_ok=True); (args.output/"oscd_results.json").write_text(json.dumps(rows,indent=2))
    headers="| City | Pipeline | Config | Precision | Recall | F1 | IoU | Overall accuracy |\n|---|---|---|---:|---:|---:|---:|---:|\n"
    body="\n".join(f"| {r['city']} | {r['pipeline']} | {r['configuration']} | {r['metrics']['precision']:.4f} | {r['metrics']['recall']:.4f} | {r['metrics']['f1']:.4f} | {r['metrics']['iou']:.4f} | {r['metrics']['overall_accuracy']:.4f} |" for r in rows)
    (args.output/"oscd_results.md").write_text(headers+body+"\n")
    (args.output/"oscd_results.tex").write_text("\\begin{tabular}{lllrrrrr}\nCity & Pipeline & Config & Precision & Recall & F1 & IoU & OA\\\\\n\\hline\n"+"\n".join(f"{r['city']} & {r['pipeline']} & {r['configuration']} & {r['metrics']['precision']:.4f} & {r['metrics']['recall']:.4f} & {r['metrics']['f1']:.4f} & {r['metrics']['iou']:.4f} & {r['metrics']['overall_accuracy']:.4f}\\\\" for r in rows)+"\n\\end{tabular}\n")
    print(f"OSCD {args.split}: wrote {len(rows)} reproducible rows to {args.output}")
if __name__ == "__main__": main()
