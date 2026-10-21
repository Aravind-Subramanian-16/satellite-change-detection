# Reviewer Q&A — 20 questions

Rules for answering:

- Quote only saved v2 numbers or a file in the repository.
- Say “unverified” when the evidence is absent; do not improvise an estimate.
- Never claim novelty, priority, operational accuracy or improvement from the
  unrun protocol.
- If a question asks for a baseline you do not have, say so and point to
  `TODO_CITATIONS.md`.
- Prefer the limitation over a defensive answer. The paper is stronger when its
  boundary is explicit.

---

### 1. What is the contribution?

An auditable implementation of a Sentinel-2 decision-support tool, a
train-only benchmark of simple spectral rules and one CNN on the official OSCD
test cities, and a preregistered validation-only protocol whose test score is
left uncomputed. The contribution is the evidence and the reporting discipline,
not a new detector. There is no priority or state-of-the-art claim.

### 2. Why is the best F1 only 0.1176?

The percentile spectral rule is deliberately simple: an NDVI/NDBI difference
threshold selected on training cities, no SCL in the benchmark, no MMU,
compositing or PIF. It under-predicts change (1.66% predicted vs. 5.17% true).
On a 5.17% positive class, F1 is sensitive to both misses and false positives;
a transparent rule with a single threshold does not capture heterogeneous urban
change. The result is weak and we report it as such.

### 3. Isn’t that far worse than published OSCD methods?

Probably, but we do not make a comparable baseline claim. Published OSCD
models use different architectures, training data, label handling and
protocols; we have not implemented any of them under this exact split and
metric. `TODO_CITATIONS.md` records the missing verified baseline comparison.
The paper explicitly says it is not a competitive score. Quoting a number from
an incompatible protocol would be worse than having no comparison.

### 4. Why compare a CNN trained on aerial LEVIR-CD imagery to Sentinel-2?

Because that checkpoint is the one provided with the project, and the question
was whether it transfers. It is described as trained on 0.5 m aerial pairs, not
on OSCD, and it predicts almost nothing (joint-percentile F1 0.0007, 0.01%
predicted; reflectance F1 0.0000, 0.00% predicted). That is negative transfer,
reported as measured. One checkpoint cannot establish that “CNNs fail on OSCD”;
the paper says the domain-gap explanation is plausible, not causal.

### 5. Why didn’t you fine-tune the CNN on OSCD?

Fine-tuning code exists (`benchmarks/finetune_cnn.py`) but has not been run;
the OSCD data and compute were not available locally, and the torch-only test
is skipped. Running it would create a different system, not a reproduction of
the v2 CNN. The learned classifier and auto-improvement notebooks are the
owner-run paths. Until they are run and pasted, there is no fine-tuned result
to report.

### 6. Otsu has OA 0.3439 — why is that the headline rather than its F1?

Otsu predicts 67.35% of pixels as changed on a 5.17% positive class, so its
overall accuracy is dominated by the minority-class errors. Its recall is high
(0.6684) but precision is 0.0513, giving F1 0.0953. Reporting F1 alone would
hide the over-prediction; reporting OA as if it were comparable to F1 would be
misleading. The tables label Otsu's score as OA and show F1 only for
completeness. The number is not a success.

### 7. Did you tune on the test split?

No thresholds or preprocessing were selected on the test cities for v2. The
hardcoded rule used training-selected NDVI −0.30 / NDBI +0.30 (both at the
grid edge), percentile used 99.0, and CNN joint-percentile was chosen on
training cities. However, the test split was used in an earlier preliminary
run with a smaller grid, disclosed with pooled F1 percentile 0.167, hardcoded
0.104, Otsu 0.095 and CNN 0.0. v2 is therefore not an independent confirmation.
There was no post-v2 test tuning.

### 8. Why are there no confidence intervals or significance tests?

Ten cities and one label source; we treat the numbers as descriptive. Pooling
3 million pixels would give artificially narrow intervals because pixels are
not independent. The paper explicitly declines population estimates and
significance claims. City-level bootstrap intervals would be a useful addition,
but they would not turn ten cities into a broad sample.

### 9. What is v3, and why hasn’t it been run?

v3 is a frozen one-shot scoring event for four systems: the percentile
reference (S0), the auto-improved spectral system (S1), the learned classifier
(S2) and fusion (S3), with fixed metrics and no post-test tuning. It is
documented in `docs/paper/PREREGISTRATION.md`. It has not been run because the
OSCD data and learned artifacts are absent locally, no auto-improve log
exists, and no protocol-compliant v3 scorer is included in the checkout. The
paper reports no v3 number. The scorer must be written and tested **before**
test access; it cannot be improvised after seeing v3 data.

### 10. Is the learned 55-feature classifier any good?

Unknown. It is implemented and synthetic-tested, disabled by default, and has
no test-city score in this checkout. Its Colab notebook was not run locally and
no output was pasted. The interface shows `display_metrics: false` for it. No
accuracy number is claimed or displayed.

### 11. How do you prevent showing accuracy for unvalidated profiles?

`profiles/validation_status.json` marks built-up as quantitatively benchmarked
on OSCD urban change (pooled F1 about 0.12) and all other profiles as
unvalidated. The API sets `display_metrics: false` for unvalidated profiles,
and the UI shows a validation-status badge without an F1. Tests assert that the
unvalidated banner contains no “F1”. This is a product and test-level guard,
not just a documentation statement.

### 12. How is provenance recorded?

Each result records the code commit, app version, pipeline, profile,
thresholds, scene IDs, dates, percent masked and a UTC timestamp; optional
compositing/normalisation/MMU settings are included when used. The same fields
appear in exports and the PDF report, and the v2 figure manifest records the
source JSON hash. This is implemented in `provenance.py` with tests in
`tests/test_provenance.py`, `test_live_api.py`, `test_exports_and_osm.py` and
`test_reports.py`.

### 13. What about clouds and shadows?

The live path uses Sentinel-2 SCL classes 3, 8, 9 and 10 for cloud/shadow
masking, warns above a configurable cloud fraction, and returns HTTP 422 with
candidate scenes if a window is fully masked. The benchmark layout used for v2
does not include SCL, so cloud-mask quality is **not evaluated** by the scores.
The paper states this; any cloud-mask accuracy claim would be unsupported.

### 14. Why 10 m resolution, and can it detect roads?

OSCD is Sentinel-2 at 10/20 m. Roads narrower than about 20 m are mostly
sub-pixel, so the tool does not claim road detection. The roads profile reports
“changed area within X m of mapped roads” as context only, using cached OSM
data with ODbL attribution. A road claim would need sub-metre imagery,
centreline labels and a different method; that is future work, not a result.

### 15. Is the heatmap a probability?

No. It displays rule magnitude/evidence, not a calibrated probability. The UI
legend says so, the canvas has a descriptive `role="img"` label, and the
palette is viridis for colour-blind safety and monotonic luminance. The learned
pipeline's probabilities are a separate experimental path and are not
calibrated or validated here. `uncertainty.py` exists, but real ECE is
unverified.

### 16. Can I deploy this publicly as-is?

No, not safely. There is no authentication; `/history` exposes stored previews,
AOIs and results to anyone who can reach the service. Rate limiting is
in-process and resets on restart. Docker and GitHub Actions are unverified.
A public deployment needs an authenticated proxy, a retention/deletion policy,
a shared rate-limit store and a licence review. The app is a decision-support
prototype, not an operational service.

### 17. What about the data licences and commercial use?

OSCD labels are reported as CC BY-NC-SA in this project; the licence must be
verified at the official source, and the non-commercial clause may prohibit
commercial use. Copernicus Sentinel data and OSM/Overpass have their own terms
(ODbL for OSM). The repository does not redistribute OSCD imagery, labels or
model weights. Legal review is required before redistribution, commercial
deployment or a commercial venue submission. No code `LICENSE` file exists yet;
that is a submission blocker.

### 18. Is this novel? Is it the first tool of its kind?

We do not know, and the paper does not claim either. `NOVELTY_CHECKLIST.md`
records a shallow web search per contribution; it is not a systematic review,
and every status is **unverified**. Related work, commercial decision-support
tools and open change-detection tools exist. The work is framed as an
implementation and evaluation report, not as a first or novel method. Any
priority claim requires an external, documented search.

### 19. What would change your conclusion?

A genuinely held-out city set never used for scoring, showing a materially
different percentile F1; a second CNN checkpoint trained on Sentinel-2 with
non-trivial recall; a benchmark with SCL showing that cloud masking changes
the spectral scores; labelled agriculture/deforestation data showing the
non-urban profiles work or fail; a multi-seed study showing the percentile vs.
hardcoded difference is within variation; or a human study showing whether
operators verify candidates or defer to the heatmap. Another number on the same
ten cities would not.

### 20. Why should this be published, and who cares?

The value is an auditable negative result and a concrete implementation
pattern: provenance on every result, validation gating in the interface,
disclosed repeated test use, and a preregistered protocol left uncomputed
rather than overclaimed. Researchers comparing OSCD methods can use the
protocol and the disclosed numbers; practitioners can reuse the provenance and
validation-status design. It is not a state-of-the-art result, and the venue
must accept that scope. If the only acceptable contribution is a higher score,
this paper is not the right fit.

---

## If you get a question you cannot answer

Say: “That is not in the saved results; I can point you to the file that would
answer it, or mark it as unverified.” Then name the file or the missing
artifact. Do not estimate, do not average across cities on the spot, and do not
promise a v3 number.
