# OSCD benchmark notes

Pipeline B is evaluated with the application implementation in `spectral_pipeline.py`: NDVI decrease or NDBI increase, optional Otsu/percentile thresholds, and SCL exclusion where SCL exists. Threshold adaptation must be selected on OSCD training cities only; test cities are evaluation-only.

There are no OSCD scores in this repository yet: the OSCD files are absent, and
inventing results would invalidate the paper. `benchmarks/oscd_eval.py` reads
the official archive layout directly (rather than prepared adapters), validates
all five selected band dimensions against each `cm.png`, and checkpoints its
JSON plus Markdown per-city/aggregate tables. Its outputs are the source of
record for tables.

Limitations: OSCD is a small, imbalanced urban-change benchmark with mixed native band resolutions. It does not provide Sentinel-2 SCL, therefore cloud-mask ablations cannot be measured on it. Pipeline A is trained on 0.5m LEVIR-CD imagery; applying it to OSCD 10m data is a domain-gap stress test, not a retrained comparison.
