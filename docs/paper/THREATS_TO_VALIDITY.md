# Threats to validity

This document accompanies `paper.tex` and `CLAIMS_AUDIT.md`. It states where the
reported v2 evidence can fail, which failures are measurable, and which are not.
It does not replace the numbers or add new ones.

Source of record: `benchmarks/results/oscd_results_v2.json` (SHA-256
`37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f`), rendered
in `benchmarks/results/oscd_results_v2.md` and `PAPER_NOTES.md`. The benchmark
scored 3,077,936 pooled test pixels, of which 5.17% are labelled change.

## 1. Claim boundary

The paper claims:

- a description of the implemented tool and its provenance/validation-status
  behaviour;
- pooled and per-city v2 scores for five configurations on the official OSCD
  test cities;
- the observation that the evaluated CNN transferred poorly under this
  protocol;
- the existence of a preregistered, validation-only protocol whose test score
  is uncomputed.

It does **not** claim a new method, a competitive OSCD score, operational
accuracy, non-urban profile accuracy, cloud-mask quality, causal attribution of
the CNN failure, or that the protocol improves test performance.

Any statement outside that boundary is a validity error even if the underlying
code exists.

## 2. Construct validity

*Does the experiment measure the intended construct — useful urban change
detection — or a proxy?*

| Threat | Evidence | Direction / severity | Mitigation in the paper | Residual risk |
|---|---|---|---|---|
| **Label construct is narrow.** OSCD labels urban change only. | Dataset description; the paper says "urban change only". | Agriculture, deforestation, water and road change are not measured. High if the tool is read as general. | Profiles for those tasks are explicitly unvalidated; no accuracy number is shown for them. | The tool can still be misread as validated for general change; interface wording and limitation text are the only guard. |
| **"Change" is a binary label, not a decision outcome.** | Metrics are pixel TP/FP/FN/TN against binary masks. | F1 measures pixel overlap, not whether an operator would act. Moderate to high. | Paper calls the tool decision support and emits candidates, not autonomous polygons. | No user study or cost model; F1 0.1176 does not translate to a workflow benefit. |
| **Cloud/shadow masking is not evaluated.** | The benchmark layout lacks SCL; only the live path masks classes 3/8/9/10. | Benchmark scores may include cloudy/shadowed pixels; live behaviour differs. Moderate. | Paper states this explicitly; `docs/LIMITATIONS.md` repeats it. | Mask quality, false masking and cloud-edge artifacts are unquantified. |
| **Otsu headline is overall accuracy, not F1.** | Otsu predicts 67.35% changed; OA 0.3439; F1 0.0953. | OA is dominated by the unchanged class and is not comparable to F1. High if mixed. | Every table and figure labels Otsu's reported score as OA; F1 is marked "for completeness". | A reader can still quote 0.3439 as if it were comparable; the caption cannot prevent that. |
| **CNN preprocessing variants are not a model comparison.** | Only one checkpoint and two preprocessing variants; no retraining on OSCD. | Cannot separate architecture, weights, preprocessing and sensor gap. High for causal claims. | Paper explicitly says the domain-gap explanation is plausible, not causal. | Readers may still infer that "CNNs fail on OSCD"; the evidence is one checkpoint. |
| **Spectral rule is a simple difference threshold.** | Hardcoded NDVI/NDBI thresholds; percentile on change evidence; no learned spectral model in v2. | The benchmark tests a deliberately simple baseline, not the best spectral method. Moderate. | Paper calls the rules transparent but weak and does not claim competitive performance. | The score may understate what a tuned spectral method could do; it is not a literature baseline. |
| **The tool's "confidence" is a rule magnitude, not a probability.** | Heatmap is labelled as evidence magnitude; no calibration in v2. | Users may treat brightness as probability. Moderate. | UI legend and paper state it is not a probability; calibration is not claimed. | Visual salience can still imply certainty; no user testing. |

## 3. Internal validity

*Could the measured association be caused by the protocol rather than the
methods?*

### 3.1 Threshold and preprocessing selection

The paper states that thresholds and CNN preprocessing were selected on the 14
training cities. The hardcoded values are NDVI drop `-0.30` and NDBI rise
`+0.30`; both are at the edge of the search grid. Percentile mode selected
`99.0`; CNN joint-percentile is marked "chosen on train". This is a defensible
train/test separation **provided the selection code and logs are accurate**.

Residual threats:

- **Grid-edge selection.** Both hardcoded thresholds sit at the grid boundary,
  so the selected rule may be constrained by the grid rather than by the data.
  The direction is unknown: a wider grid could improve or degrade test F1.
  Severity: moderate for interpreting the hardcoded score as an optimum.
- **No retained selection log for every choice.** `PAPER_NOTES.md` says the JSON
  records selected configurations but does not retain the CNN's training
  scores. The selection is documented, not fully replayable from the result
  file. Severity: moderate for auditability.
- **Training-city heterogeneity.** The 14 training cities differ from the 10
  test cities; a train-only selection can still overfit the training
  distribution. Severity: moderate and unavoidable without nested CV.

### 3.2 Repeated use of the test split

Two test-scoring events preceded the paper:

1. a preliminary run with a smaller grid: pooled F1 percentile 0.167,
   hardcoded 0.104, Otsu 0.095, CNN 0.0;
2. the v2 run used here: percentile 0.1176, hardcoded 0.0782, Otsu 0.0953,
   CNN 0.0007 / 0.0000.

The preliminary run is disclosed. This means the test split is **not pristine**
and the v2 numbers are **not an independent confirmation** of the preliminary
values. No post-v2 test tuning is reported. A third one-shot v3 scoring event
is preregistered but has not been run.

Severity: **high for any claim of unbiased generalization**, low for the
descriptive claim "these are the measured v2 scores". The paper makes only the
latter. The earlier values also differ materially from v2 (0.167 vs 0.1176 for
percentile), which is a warning that test-set decisions matter.

### 3.3 Benchmark path versus deployed path

The offline benchmark computes NDVI/NDBI from reflectance bands and does not use
SCL, compositing, MMU, PIF normalisation or morphology. The live tool uses a
different data path (RGB preview plus encoded NDVI/NDBI/SCL) and can enable
those options. Therefore:

- the v2 scores do not validate the deployed live path end to end;
- options that are off by default are not represented in the scores;
- the browser and API have separate failure modes (scene selection, masking,
  upload validation) that the benchmark does not exercise.

Severity: high if the paper is read as validating the web application's output.
The paper describes the benchmark as an offline evaluation of the rule logic.

### 3.4 Checkpoint provenance and artefact absence

The CNN checkpoint is described as trained on LEVIR-CD (0.5 m aerial pairs).
The checkpoint and OSCD imagery are absent from this checkout. The following
cannot be verified locally:

- checkpoint identity, training split, preprocessing at training time;
- the exact inference environment and numerical reproducibility of the CNN
  rows;
- whether the joint-percentile variant was selected using only training cities
  (documented, but the selection log is not retained).

Severity: **high for reproducing the CNN result**; the spectral rows are
simpler and backed by the saved JSON, but their original run also cannot be
re-executed without OSCD data.

### 3.5 Determinism and seeds

The spectral rules are deterministic given data and thresholds. The CNN
inference should be deterministic on CPU for a fixed checkpoint and input, but
runtime/hardware differences can change floating-point results and therefore
borderline pixels. No seed-variance study was run. Severity: low for the gross
spectral conclusions, moderate for exact CNN counts.

### 3.6 Metric arithmetic

Pooled values are computed from summed confusion counts, not by averaging city
F1. The v2 JSON was independently recomputed during this project; pooled
precision/recall/F1/OA match the Markdown. Remaining risks are rounding in the
displayed percentages and the treatment of zero-denominator cases:

- CNN reflectance has zero predicted positives, so precision is defined here as
  0 rather than undefined;
- cities with zero predicted change contribute zero TP/FP;
- Otsu's F1 is reported despite its very low precision, but OA is the headline.

Severity: low for the reported values, moderate for cross-paper comparison if
another paper defines zero-denominator metrics differently.

## 4. External validity

*Do the results generalize beyond the ten test cities and this sensor?*

| Threat | Evidence | Direction / severity | Mitigation | Residual risk |
|---|---|---|---|---|
| **Ten cities only.** | 10 official test cities; per-city percentile F1 0.0005–0.2481. | The pooled score hides large heterogeneity; city-level ranking is unstable. High for population claims. | Per-city table and figure; no confidence intervals claimed. | No basis for a global accuracy estimate. |
| **Geographic and seasonal coverage.** | Cities include Europe, South America, Asia and the Middle East; acquisition dates and seasons vary. | Performance may depend on biome, season, urban form and atmospheric conditions. Unknown direction. | Paper names the variation and declines causal attribution. | No stratified analysis by biome/season. |
| **Sentinel-2 10 m only.** | B04/B08/B11 at 10/20 m; labels at the same grid. | Sub-pixel roads and small structures are not resolvable; results will not transfer directly to 0.5 m or 30 m data. High for roads. | Roads profile explicitly says sub-pixel; no road accuracy is claimed. | Users may still apply the urban score to road monitoring. |
| **OSCD acquisition era and processing baseline.** | The benchmark uses the released OSCD pairs. | Atmospheric correction, sensor calibration and urban change patterns may differ from current data. Moderate. | No temporal generalization claim. | Live-tool results on new scenes may differ from benchmark behaviour. |
| **Urban-change label definition.** | OSCD labels are binary urban change, not a universal ontology. | A "change" in another application may not match the label. High for cross-domain use. | Paper restricts claims to OSCD urban change. | No ontology mapping or cross-dataset test. |
| **Live tool options not validated.** | PIF, compositing, MMU, morphology, learned classifier, fusion, uncertainty are implemented but off by default and unscored. | Any accuracy implied for those options would be unsupported. High. | Interface suppresses accuracy for unvalidated profiles; paper says they are not validated. | A user can still enable an option and misinterpret output. |
| **Operational deployment.** | No authentication, in-process rate limits, local history, no field validation. | The app is a demonstration/decision-support prototype, not an operational service. High for production claims. | `docs/LIMITATIONS.md` and `DEPLOY.md` state the gaps. | Deployment by a third party could expose data or overstate readiness. |

## 5. Statistical conclusion validity

- **No confidence intervals or significance tests.** Ten cities and one label
  source; the paper calls the numbers descriptive. Any "better than" statement
  about percentile vs hardcoded (0.1176 vs 0.0782) is a point-estimate
  difference, not a tested effect. The per-city ranking reverses in several
  cities (hardcoded exceeds percentile in norcia, saclay_w, rio and chongqing;
  the two are nearly tied in valencia), which makes a uniform superiority claim
  unsafe.
- **Pseudo-replication.** Pooling 3,077,936 pixels makes intervals artificially
  narrow if pixels are treated as independent. The paper does not compute
  pixel-level CIs; city is the more defensible unit, and there are only ten.
- **Class imbalance.** True change is 5.17%. OA differences of a few points can
  reflect tiny prediction differences; F1 and predicted fraction are more
  informative. Otsu's OA is not comparable to F1.
- **Zero/near-zero cells.** CNN joint-percentile has 0.01% predicted change;
  small count differences can change F1 by more than the reported third decimal.
  The exact values should not be over-interpreted.
- **Single checkpoint, two preprocessing variants.** No architecture or seed
  ensemble; the CNN result is one draw, not a distribution.
- **Threshold selection at grid edge.** The hardcoded result may be limited by
  the search grid; this is a design limitation, not a significance issue.

## 6. Reproducibility validity

- The v2 JSON and Markdown are tracked; the figure generator verifies all ten
  cities and five configurations before plotting. The source hash is recorded
  in `figures/figure_manifest.json`.
- OSCD imagery, labels and the CNN checkpoint are **not** in the checkout. The
  benchmark and CNN rows cannot be re-executed from this repository alone.
- The paper's code commit for the v2 numbers is Phase E `a6dad9e`. Phase F
  changes are documentation/figures/tests; this must be rechecked if the
  benchmark code changes.
- Dependency ranges are pinned to compatible major/minor versions, but no
  lockfile or container image digest is recorded for the original v2 run.
- The Colab learned-classifier and auto-improve notebooks were not run locally
  and have no pasted outputs. They are unverified, not reproducible evidence.
- LaTeX could not be compiled in this environment (`pdflatex`, `tectonic` and
  `latexmk` are absent). The manuscript and generated tables are therefore
  structurally reviewed but not PDF-verified.

See `REPRODUCIBILITY.md` for commands, hashes and the exact unverified items.

## 7. Ethical, legal and dual-use validity

- **Automation bias.** A polished map with a heatmap can be read as ground
  truth. The UI says decision support and the paper says human verification is
  required, but no user study measures whether that warning works. Severity:
  high for deployment without training.
- **Dual use.** The tool is intended for civil land observation. It is not a
  targeting or enforcement system, but change detection is dual-use. The paper
  states the intended use; it cannot control downstream use.
- **Privacy.** The app stores previews and AOI locations in a local SQLite
  history. No authentication is implemented. A public deployment would create
  privacy and access-control risks. This is a deployment limitation, not a
  benchmark finding.
- **Licensing.** OSCD terms (reported as CC BY-NC-SA; verify at source) may
  restrict commercial use; OSM context is ODbL; Copernicus data has its own
  terms. The repository does not redistribute OSCD imagery or labels. Legal
  review is required before any commercial deployment or redistribution.
- **AI-assistance disclosure.** The manuscript and code were prepared with AI
  assistance. The submission checklist records the need to disclose this under
  the chosen venue's policy.

## 8. Threat summary

| Validity type | Main threat | Severity | Can it be fixed with existing evidence? |
|---|---|---|---|
| Construct | OSCD urban labels are not operational usefulness | High | No; needs field/user study |
| Construct | Cloud masking not evaluated | Moderate | No; needs SCL-preserving benchmark |
| Internal | Test split used twice before the paper | High for generalization | Only by a genuinely new, one-shot test set |
| Internal | CNN checkpoint/data absent, provenance not locally verifiable | High for reproduction | Owner must supply artefacts |
| Internal | Grid-edge thresholds | Moderate | A wider pre-registered search could test it; not done |
| External | Ten cities, one sensor, one label source | High | New multi-sensor, multi-region labels needed |
| External | Non-urban profiles unvalidated | High for their use | Labelled data needed |
| Statistical | No CIs, city-level heterogeneity, pseudo-replication | Moderate–high | City-level intervals possible; would not fix n=10 |
| Reproducibility | Imagery/weights absent; LaTeX not compiled; Colab unrun | High | Owner actions listed in `REPRODUCIBILITY.md` |
| Ethics/legal | Automation bias, dual use, privacy, OSCD licence | High for deployment | Human review, legal review, authentication |

## 9. What would change the conclusions

- A genuinely held-out, never-scored city set showing percentile F1 far above
  or below 0.1176.
- A second CNN checkpoint trained on Sentinel-2 showing non-trivial recall;
  that would weaken the "negative transfer" reading (it would not erase the
  measured result for this checkpoint).
- A benchmark with SCL showing that cloud masking materially changes the
  spectral scores.
- Labelled agriculture/deforestation data showing that the unvalidated profiles
  perform acceptably — or fail.
- A pre-registered multi-seed study showing that percentile vs hardcoded
  differences are within run-to-run or city-to-city variation.
- A user study showing whether operators actually verify candidates or defer to
  the heatmap.

Until at least one of these exists, the paper's descriptive and negative
framing is the strongest defensible claim.

## 10. Bottom line

The v2 numbers are internally consistent and honestly limited: they are
descriptive scores on a small, previously used official test split, produced by
simple rules and one mismatched CNN. They do not establish operational
accuracy, general change-detection ability, method novelty or improvement from
the unrun validation protocol. Every use of these numbers should carry the
city count, the single label source and the two prior scoring events.
