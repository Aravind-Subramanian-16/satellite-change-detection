# Pre-registration: OSCD test scoring (Phase D2.6)

Status: **frozen protocol, committed before any v3 scoring**. No
`oscd_results_v3.json` or `.md` exists in this repository at the time of this
commit. The v2 test scoring event and its earlier preliminary run are already
disclosed in `README.md` and `PAPER_NOTES.md`; they are not independent evidence
for v3.

Date: 2026-10-21. Any later change to this file must be an explicit amendment
recorded **before** the test split is read again, with the reason and date.

## 1. Scope

One scoring event on the official ten OSCD test cities for the frozen systems
below. The event measures held-out generalisation only. No system is selected,
tuned, calibrated, or re-run after seeing v3 results. The v2 files remain
unchanged.

## 2. Frozen inputs

Before test access, the scorer must verify:

1. `benchmarks/results/auto_improve_log.json` exists, has
   `metadata.test_split_read: false`, `metadata.complete: true`, and records all
   12 pre-registered trials.
2. The log's `recommendation.final_fit` contains the exact spectral system and
   threshold parameters fit on all 14 training cities.
3. The optional learned artifact is a joblib bundle whose metadata contains
   `test_split_scored: false`, `fit_cities` (11) and
   `held_out_train_cities` (3). Its SHA-256 is recorded in the v3 metadata.
4. The optional fusion configuration JSON contains the fixed weight and
   threshold selected on the three held-out TRAIN cities, with its SHA-256 and
   `test_split_read: false`.
5. No v3 result file exists. If it does, the scorer aborts rather than
   overwriting or appending a second event.

Artifacts that are absent are skipped and named in the v3 metadata. They are
not replaced by a different model or by values chosen after test access.

## 3. Frozen systems

| ID | System | Exact definition |
|---|---|---|
| S0 | Percentile reference | The v2 training-selected spectral configuration: `mode=percentile`, `percentile=99.0`, NDVI-drop/NDBI-rise directions from `spectral_pipeline.py`, no SCL mask (OSCD layout has no SCL). |
| S1 | Auto-improved spectral | The system named by `auto_improve_log.json` → `recommendation.system`, with `recommendation.final_fit.params`; optional PIF/cleanup/MMU exactly as recorded in that system's component tuple. |
| S2 | Learned pixel classifier | The 55-feature HistGradientBoosting joblib trained on 11 TRAIN cities, with the probability threshold stored in the bundle. No retraining for v3. |
| S3 | Fusion | Robust-normalised spectral evidence fused with S2 probability using the weight and threshold in the frozen fusion configuration JSON. S3 is skipped if S2 or its fusion configuration is absent. |

S0 is a reference for the new event, not a claim that v2 and v3 are directly
comparable without the disclosure above. S1 is the only system chosen by the
auto-improvement procedure; the selection is made on training cities only.

The uncertainty/agreement analysis (`uncertainty.py`) is a **held-out TRAIN
diagnostic**. It is not a separate test system and no test-set calibration
claim will be made.

## 4. Fixed metrics

For each scored system, report:

- Pooled pixel precision, recall, F1, IoU, overall accuracy, predicted-change
  fraction and true-change fraction over the ten test cities.
- Per-city F1, and the mean, sample standard deviation, minimum and maximum
  across the ten cities.
- Paired per-city F1 differences for S1 − S0 (and S2/S3 when present), with
  mean, median, minimum and maximum. These are descriptive; no significance
  test is pre-registered and none will be added post hoc.
- Runtime and the number of test cities scored.
- A clear marker of which systems were skipped and why.

Fractions are percentages. True change is constant across systems for a given
event and is reported once. There is no pooled “best” selection after scoring.

## 5. Fixed selection rule (training only)

- Auto-improvement selects the system with the highest pooled leave-one-city-out
  validation F1; ties by precision, then recall, then fewer components.
- Components whose mean paired held-out-city F1 delta is ≤ 0 are dropped; the
  recommendation is the highest-F1 remaining system and its parameters are
  refit on all 14 training cities.
- The learned threshold is the maximum-F1 threshold on the three seeded
  held-out TRAIN cities from the training artifact.
- Fusion weight and threshold maximise F1 on the same held-out TRAIN cities.
- No test city enters any of these steps. The hard guards in
  `learned_features.assert_no_test_cities`, `auto_improve.py`, and the training
  scripts must remain in force.

## 6. Scoring protocol

1. Run the scorer once with the frozen artifacts and record:
   `scoring_event: 3`, UTC timestamp, code commit, artifact SHA-256 hashes,
   system definitions, and the exact command.
2. Write only `benchmarks/results/oscd_results_v3.json` and
   `oscd_results_v3.md`. Never overwrite or delete v2 files.
3. If the process is interrupted before completion, resume the **same** event
   with identical configs; the log must show one event and the same hashes.
4. After completion, do not change thresholds, components, features or fusion
   weights. Any such change is a new, separately disclosed experiment, not a
   correction to v3.
5. Copy the v3 files into the repository and update the paper only from the
   saved JSON/MD. Do not transcribe numbers by hand without a cross-check.

## 7. Reporting rule

v3 will be reported whether it improves or worsens S0. Negative results and
per-city variance are required. No priority or superiority claim may be added
on the basis of v3 alone; see `NOVELTY_CHECKLIST.md` and `CLAIMS_AUDIT.md`
(Phase F).

## 8. Current status

Test scoring is **not performed** in this checkout. OSCD imagery, labels and
the optional learned artifacts are absent locally. The owner must run the
training/auto-improvement notebooks and this frozen protocol on Colab, then
paste the v3 output for verification. Until then, no v3 number exists.
