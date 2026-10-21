# Transparent Sentinel-2 change detection — 12-slide deck

Target length: 12–15 minutes plus questions. Every number below is from
`benchmarks/results/oscd_results_v2.json` / `.md` or is explicitly marked
unverified. Do not add a score that is not in the saved results.

---

## Slide 1 — Title

**Transparent Sentinel-2 Change Detection as Decision Support**

A reproducible OSCD benchmark of spectral rules and a learned baseline

- Auditable implementation
- Negative transfer reported as measured
- A preregistered protocol whose test score is deliberately uncomputed

**Speaker notes:** This is not a “new model” talk. It is an audit of a working
tool and a small benchmark. The headline is that simple spectral rules are weak
but inspectable, a mismatched CNN fails, and the evaluation itself has a
disclosed history. Ask the audience to hold two questions: what is actually
validated, and what would change the conclusion?

---

## Slide 2 — The problem: a score is not an audit trail

- Operational tools need to know **which scenes, dates, masks and thresholds**
  produced a result.
- A single accuracy number hides class imbalance and near-empty predictions.
- Unvalidated analysis profiles must not display accuracy numbers.
- Test sets get reused; improvement claims need a protocol.

**Speaker notes:** Decision support is different from a leaderboard. If an
analyst cannot reconstruct why a polygon appeared, the score does not help.
This project treats provenance and validation status as first-class outputs,
not as metadata added after the fact. The next slides show the implementation
and then the measurement.

---

## Slide 3 — System overview

```
Leaflet AOI picker
  -> Copernicus scene ranking (date, cloud, coverage)
  -> before/after fetch + SCL cloud/shadow masking
  -> spectral profile (general / agriculture / deforestation / built-up / roads)
  -> optional CNN or learned path (flags, off by default)
  -> regions, stats, heatmap, GeoJSON/CSV/PDF
  -> provenance: commit, scenes, dates, thresholds, masked %, timestamp
```

- Profiles are declarative; the general profile remains the default.
- The learned endpoint is disabled unless explicitly enabled.
- Every result carries a request ID and provenance.

**Speaker notes:** This is the deployed path. The offline benchmark is simpler:
it computes NDVI/NDBI from reflectance and does not use SCL, compositing, MMU or
PIF. That difference matters and is stated in the paper. The UI is a real
FastAPI + static front end; the browser screenshots in the repo include mocked
API runs for UI wiring, not real Copernicus analyses.

---

## Slide 4 — Data and protocol

- OSCD: 14 training cities, 10 official test cities, Sentinel-2 urban change.
- Thresholds and CNN preprocessing selected on **training cities only**.
- v2 pooled test pixels: **3,077,936**; true change **5.17%**.
- Pooled metrics from summed confusion counts, not averaged city scores.
- Two prior test-scoring events are disclosed; v2 is not independent
  confirmation.
- v3 is preregistered but **not run**.

**Speaker notes:** The true-change fraction is the key context for every score.
A method that predicts almost nothing can still get high overall accuracy.
The preliminary run had percentile F1 0.167, hardcoded 0.104, Otsu 0.095 and
CNN 0.0; v2 is the source of record, and the difference between events is part
of the honesty story, not something to hide.

---

## Slide 5 — Methods in one slide

- **Hardcoded:** ΔNDVI < −0.30 or ΔNDBI > +0.30; both at the search-grid edge.
- **Percentile:** threshold positive change evidence at the 99.0th percentile
  (training-selected).
- **Otsu:** label-free histogram threshold; predicts **67.35%** changed.
- **CNN:** existing two-input model; joint-percentile preprocessing chosen on
  train; reflectance variant reported as the other configuration.
- **Metrics:** precision, recall, F1, IoU, OA, predicted fraction; pooled from
  TP/FP/FN/TN.

**Speaker notes:** The spectral rules are deliberately simple and inspectable.
The hardcoded thresholds sit at the edge of the grid, so the grid may be
limiting the result; that is a finding about the experiment, not a claim that a
wider grid would fix it. Otsu is not a drop-in improvement: it buys recall with
very low precision.

---

## Slide 6 — Pooled v2 results

| Method | Pred. % | Precision | Recall | F1 | OA | Reported |
|---|---:|---:|---:|---:|---:|---|
| Hardcoded | 2.24 | 0.1292 | 0.0561 | 0.0782 | 0.9317 | F1 |
| Percentile | 1.66 | 0.2419 | 0.0777 | **0.1176** | 0.9397 | F1 |
| CNN joint | 0.01 | 0.2983 | 0.0003 | 0.0007 | 0.9483 | F1 |
| CNN reflectance | 0.00 | 0.0000 | 0.0000 | 0.0000 | 0.9483 | F1 |
| Otsu | 67.35 | 0.0513 | 0.6684 | 0.0953 | **0.3439** | OA |

True change: **5.17%**. Otsu's headline is OA, not F1.

**Speaker notes:** The percentile rule is the best F1-scored method at 0.1176,
which is still weak. Both spectral rules under-predict change. The CNN is
essentially empty: 0.01% predicted for joint-percentile, 0.00% for reflectance.
Its OA of 0.9483 is higher than the spectral OA, which is exactly the trap:
on a 5.17% positive class, predicting almost nothing looks accurate. Do not
present the CNN OA as a success.

---

## Slide 7 — The aggregate hides the cities

- Percentile per-city F1: **0.0005** (saclay_w) to **0.2481** (chongqing).
- Hardcoded: **0.0032** (dubai) to **0.3102** (chongqing).
- Percentile beats hardcoded on the pooled score, but not in every city
  (e.g. hardcoded is higher in norcia, saclay_w, rio and chongqing).
- Both spectral rules sit below the predicted = true line.

Show `figures/fig_per_city_f1.png` and `figures/fig_predicted_vs_true.png`.

**Speaker notes:** This is why we refuse to quote a single number without the
per-city table. Ten cities is a small sample, and the spread is larger than the
difference between the two spectral rules. The predicted-vs-true figure makes
the under-prediction visible; Otsu sits far on the over-prediction side.

---

## Slide 8 — Negative transfer, reported as measured

- The checkpoint is described as trained on **0.5 m aerial LEVIR-CD**, not on
  Sentinel-2.
- No retraining on OSCD; two preprocessing variants; one checkpoint.
- Joint-percentile: pooled F1 **0.0007**, predicted **0.01%**.
- Reflectance: pooled F1 **0.0000**, predicted **0.00%**.
- Domain/resolution/label mismatch is a plausible explanation, **not a causal
  finding**.
- We did not tune the failure away.

**Speaker notes:** This result is unsurprising in hindsight: a model trained on
a different sensor and resolution should not transfer for free. The point is
the reporting: the near-empty prediction is the finding. We do not replace F1
with OA, and we do not select a better-looking test configuration after seeing
the score. One checkpoint cannot establish that “CNNs fail on OSCD.”

---

## Slide 9 — What is not validated

- Agriculture, deforestation, roads, water: **no accuracy claim**.
- Learned 55-feature classifier: implemented, disabled by default, no test
  score.
- PIF normalisation, temporal compositing, MMU, morphology: implemented and
  synthetic-tested, not used in v2.
- Fusion, uncertainty/ECE, CNN fine-tuning: implemented, no real validation
  log.
- Otsu F1 is shown only for completeness; its headline is OA.

**Speaker notes:** The UI suppresses accuracy for unvalidated profiles and
shows a validation-status badge. That is a product decision as much as a
statistical one: it prevents a user from reading a qualitative profile as a
measured detector. The learned classifier and fusion are experimental code
paths, not validated alternatives.

---

## Slide 10 — The validation-only protocol

- 12 fixed systems; leave-one-city-out over **14 training cities**.
- Hard trial budget; every trial logged, including failures.
- Selection by pooled validation F1 only; components with ≤ 0 mean paired
  delta are dropped.
- Test cities are hard-guarded in training and search.
- v3 freezes S0 (percentile), S1 (auto-improved), S2 (learned), S3 (fusion)
  and permits **one** scoring event.
- Status: **not run**; no `oscd_results_v3.*` exists.

**Speaker notes:** This is the part that is easy to overstate. The protocol is
preregistered, but no v3 score exists. We cannot say it improves anything. The
protocol's value is that it prevents us from choosing a system after seeing
test numbers. A future runner must be written and tested before test access;
that is a blocker, not a completed result.

---

## Slide 11 — Threats to validity

- Ten cities, one sensor, one label source; no confidence intervals.
- Urban-change labels only; cloud/SCL masking not evaluated in v2.
- Test split used in two prior scoring events; v2 is descriptive, not pristine.
- CNN checkpoint/imagery absent locally; training and Colab results unverified.
- Grid-edge thresholds and one checkpoint limit causal claims.
- Automation bias, privacy (no auth/history), dual use, OSCD licence.

**Speaker notes:** The paper's limitations section is longer than its results
section for a reason. The strongest defensible claim is descriptive: these are
the measured v2 scores under a disclosed protocol. It is not a population
estimate and not operational accuracy. See `THREATS_TO_VALIDITY.md` for the
full matrix.

---

## Slide 12 — What we claim and what comes next

**Claims**

- An auditable implementation with provenance and validation gating.
- A train-only OSCD benchmark with disclosed scoring history.
- A preregistered validation-only protocol, left uncomputed.

**No claims**

- No new method, no priority, no state-of-the-art score.
- No non-urban accuracy, no cloud-mask quality, no operational readiness.

**Next:** human-in-the-loop study; labelled agriculture/deforestation data;
higher-resolution road validation; run the learned/auto-improve notebooks;
complete v3 once, without tuning.

**Speaker notes:** Close on the two questions from the start. What is validated?
Five configurations on ten urban test cities, with limitations. What would
change the conclusion? A genuinely held-out set, a second sensor, non-urban
labels, or a human study. Another number on the same ten cities would not.

---

## Live-demo script (5–7 minutes; optional)

### Before the demo

1. Use a local environment, not a public deployment:
   ```bash
   ./venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8010
   ```
2. Open `http://127.0.0.1:8010/`.
3. Confirm `/health` returns status. Do **not** claim a real Copernicus
   analysis without credentials and a valid model.
4. If `model.onnx` is absent or invalid, `/predict` returns HTTP 503 by design;
   say so before clicking.

### Demo path A — UI wiring with mocked data

Use the screenshots `docs/screenshots/phase_b_live.png`, `phase_b_scenes.png`,
`phase_b_results.png` and `phase_b_mobile.png`. They carry a visible “MOCKED
API RESPONSES / MOCKED DATA” banner. Say explicitly: “These prove UI wiring,
not a real analysis.”

### Demo path B — local UI with synthetic/injected result

1. Show the map, OSM attribution and AOI controls.
2. Draw a box; show area in km² and expected pixels; show the 10 km cap.
3. Switch profiles; point out the validation-status badge and that no accuracy
   number appears for unvalidated profiles.
4. Show the before/after slider; describe keyboard support.
5. Show the heatmap legend: “rule magnitude, not a probability.”
6. Open History; note that it is local SQLite and has no authentication — a
   deployment limitation.
7. If a valid model and sample images are available, run `/predict`; otherwise
   stop before the 503 and explain it.

### Demo path C — report/export

Use a previously generated result to download the PDF; point to the commit
hash, profile, thresholds, scene IDs, dates, masked percentage and validation
status. Do not present a mocked PDF as a real analysis.

### Demo failure script

- **503:** valid weights absent; the app fails clearly instead of crashing.
- **422 fully masked:** the selected scene has no usable pixels; suggest the
  next-best scene.
- **429:** in-process rate limit; wait for `Retry-After`.
- **413/415:** upload too large or wrong type; both are validated before
  inference.

### Do not say

- “This is validated for agriculture/deforestation/roads.”
- “The CNN is accurate because OA is 0.9483.”
- “The heatmap shows probability.”
- “The v3 protocol improves the score.”
- “This is production-ready or secure.”
- “This is novel/first/state of the art.”

---

## Timing guide

| Slides | Minutes |
|---|---:|
| 1–2 | 2 |
| 3–5 | 3 |
| 6–8 | 4 |
| 9–11 | 3 |
| 12 | 1 |
| Demo | 5–7 |
| Questions | 5+ |

If time is short, drop the live demo and use the four screenshots; never drop
slides 8, 9, 11 or 12.
