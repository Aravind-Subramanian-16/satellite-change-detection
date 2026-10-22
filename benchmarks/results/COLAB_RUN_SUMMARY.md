# Colab run summary

- Generated: 2026-10-21
- Code commit: `e8b6678b1c7f2fb19a4ac4a854c60704f29e3859`
- Pytest: `144 passed, 1 skipped, 7 warnings in 15.79s` (exit code 0)
- Scope: training-city robustness and a model load check only.

**No official OSCD test city was scored, no training or fine-tuning was run, and v3 was not run.**

## Training-city leave-one-city-out robustness

Source: `benchmarks/results/oscd_loco_thresholds.json` (SHA-256 `32d1dbf57d83a1c68c76de0d64856795c082498788428c8206fd7cf2a4a2e29d`).

Selection: For each held-out training city, choose the candidate with the highest pooled F1 over the other training cities.
Evaluation: Apply the selected candidate to the held-out training city.

| Family | Pooled held-out F1 | IoU | Precision | Recall | Distinct selected configs | Grid-edge folds |
|---|---:|---:|---:|---:|---:|---:|
| hardcoded | 0.0976 | 0.0513 | 0.0838 | 0.1168 | 2 | 14 |
| percentile | 0.1469 | 0.0793 | 0.1544 | 0.1401 | 2 | 0 |

Full-train selections (in-sample, not test results):

- hardcoded: `{"mode": "hardcoded", "ndbi_rise": 0.3, "ndvi_drop": -0.3, "use_cloud_mask": false}`; in-sample pooled F1 0.1031; grid-edge warning: WARNING: selected hardcoded value(s) at search-grid edge: ndvi_drop=-0.3, ndbi_rise=0.3
- percentile: `{"mode": "percentile", "percentile": 99.0, "use_cloud_mask": false}`; in-sample pooled F1 0.1416; grid-edge warning: None

**This is a training-split robustness check, not a test-set score.**

Caveats:
- This is a training-split robustness check, not a test-set result.
- No test city is used in this script.
- The held-out city is still a training city; its labels inform no selection in that fold.
- Full-train pooled F1 is in-sample and optimistic; it is reported only to show which configuration the grid selects.
- Otsu is excluded because it has no train-selected threshold to leave out.

## Model check

Source: `benchmarks/results/colab_model_check.json` (SHA-256 `ec452724a09c915a6577b535146bd78fe5f09dd9ce13421d8359057709c3902a`).

- File: `model.onnx`
- Size: 33,268,410 bytes (expected 33,268,410)
- SHA-256: `41c2ab6466408a6d23339a3c424307f6aa7b7f9063fe702d161b6f4685152bf9`
- onnxruntime load: yes
- Inputs: `input_a`, `input_b`
- Providers: CPUExecutionProvider

## Not run

- Official OSCD test-city scoring; no test label was read.
- Training, fine-tuning or seed variation.
- The preregistered v3 scoring event.
- Any accuracy or validation claim beyond the saved v2 results.
