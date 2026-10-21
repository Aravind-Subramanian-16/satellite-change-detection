# Claims on the 12 slides

Audit rule: every number below is copied from saved evidence, not re-computed
from new scoring. The deck generator (`scripts/make_slides.py`) asserts the
headline values before building. If a value is not in this file, do not add it
to the deck.

## Evidence used

- `degradation_results.csv` - per-image TP/FP/FN for 2,048 LEVIR-CD test pairs
  at six factors; pooled metrics are sums of counts, not means.
- `benchmarks/results/oscd_results_v2.json` - per-city OSCD v2 confusion counts.
- `benchmarks/results/oscd_evidence.json` - pooled OSCD values, analytic
  baselines and city-bootstrap intervals derived from the v2 JSON.
- `docs/paper/paper.tex` - the same values in the manuscript.
- `docs/paper/CLAIMS_AUDIT.md` - row-by-row paper audit (D1-D13, O1-O21, G1-G3).

No new test-city scoring, training, fine-tuning or v3 run was performed for the
deck.

## Slide 1 - Title

| Claim on slide | Value | Source | Status |
|---|---:|---|---|
| Pooled F1 falls from 0.5 m to 2 m | 87.06% -> 4.41% | `degradation_results.csv`; paper Table I | Measured |
| Test pairs | 2,048 | per-image CSV rows / six factors | Measured |
| "One frozen checkpoint" | one checkpoint | `docs/paper/ARTIFACT.md`; paper Sec. III | Fact about this study |

"Resolution-Induced" follows the paper title. It describes the controlled
blur-and-resampling experiment, where resolution is the manipulated factor. It
is not a claim that resolution causes the OSCD result (see slide 10).

## Slide 2 - The problem

| Claim on slide | Value | Basis |
|---|---:|---|
| Native resolution | 0.5 m LEVIR-CD | LEVIR-CD protocol; paper Sec. I/III |
| Sentinel-2 bands | 10 m and 20 m | mission specification; paper Sec. I |
| Linear ratio | 20x | 10 / 0.5 |
| Area ratio | 400x | 20 squared |
| Pixel diagram | to scale | orange square side = 1/20 of full square |

The diagram is a scale illustration, not imagery. Do not call it a simulation of
Sentinel-2 pixels.

## Slide 3 - Design

| Claim on slide | Value | Source | Status |
|---|---:|---|---|
| LEVIR-CD test pairs | 2,048 | CSV | Measured |
| Factors | 1, 2, 4, 8, 16, 20 | `evaluate_degradation.py`; paper | Protocol |
| OSCD official test cities | 10 | v2 JSON `split: test` rows | Measured set |
| OSCD pooled pixels | 3,077,936 | v2 JSON summed TN+FP+FN+TP | Measured |
| True change | 5.17% | 159,077 / 3,077,936 | Measured |
| CNN status | zero-shot weights | never trained on OSCD; paper Sec. V | Fact |
| Spectral rules | train-selected | paper Sec. II/V | Protocol |
| No SCL | benchmark layout | paper Sec. VI | Limitation |

The joint-percentile CNN *preprocessing* was selected on the training cities.
"Zero-shot" applies to the weights, not to every pipeline choice; slide 7 notes
say so explicitly.

## Slide 4 - Degradation protocol

| Claim on slide | Value | Source |
|---|---:|---|
| Blur radius | factor / 2 | `evaluate_degradation.py`; `oscd_evidence.json` pipeline spec |
| Downsample | LANCZOS to (256/f)^2 | same |
| 10 m intermediate | 12 x 12 | 256 // 20 = 12 |
| Factors to metres | 0.5, 1, 2, 4, 8, 10 | paper Table I |
| Threshold | 0.5 | paper Sec. III |
| Aggregation | pooled TP/FP/FN | CSV; paper Sec. III |

The last line of the slide is a scope statement: the transform isolates blur and
resampling and is not a Sentinel-2 simulation. This is supported by the protocol
and stated in the paper.

## Slide 5 - F1 versus resolution

| Factor | Resolution | F1 | Recall | Precision |
|---:|---:|---:|---:|---:|
| 1 | 0.5 m | 87.06% | 85.36% | 88.82% |
| 2 | 1 m | 70.81% | 57.01% | 93.43% |
| 4 | 2 m | 4.41% | 2.26% | 90.78% |
| 8 | 4 m | 2.84% | 1.44% | 97.69% |
| 16 | 8 m | 2.61% | 1.32% | 99.59% |
| 20 | 10 m | 2.61% | 1.32% | 99.47% |

All six rows are pooled from `degradation_results.csv`. The slide card shows
only 0.5 m, 1 m, 2 m and 8-10 m; the chart shows all six. "Precision rises" is
supported by the last column (88.82% to 99.47%). "Recall-dominated" is supported
by the recall drop (85.36 to 1.32) while precision rises.

## Slide 6 - Why precision misleads

| Claim on slide | Value | Source |
|---|---:|---|
| Pixels predicted changed at 10 m | 91,006 of 134,217,728 (0.068%) | CSV; paper Table I |
| True changed pixels at 10 m | 6,837,404 (5.09%) | CSV; chart only |
| Changed images with zero prediction | 924 / 935 (98.82%) | CSV; paper Table II |
| True positives | 90,527 | CSV |
| False positives | 479 | CSV |
| Precision | 99.47% | 90,527 / (90,527 + 479) |

The 5.09% in the chart is the 10 m degradation split's true-change share. It is
not the OSCD 5.17% prevalence. Do not conflate them.

## Slide 7 - OSCD transfer

| Method | Pred. % | Precision | Recall | Score | 95% city-bootstrap CI for F1 |
|---|---:|---:|---:|---:|---:|
| Hardcoded NDVI/NDBI | 2.24 | 0.1292 | 0.0561 | F1 0.0782 | 0.0168-0.1846 |
| Percentile 99.0 | 1.66 | 0.2419 | 0.0777 | F1 0.1176 | 0.0540-0.1802 |
| Otsu | 67.35 | 0.0513 | 0.6684 | OA 0.3439 | F1 0.0953; 0.0495-0.1245 |
| CNN joint percentile | 0.01 | 0.2983 | 0.0003 | F1 0.0007 | 0.0000-0.0017 |
| CNN reflectance | 0.00 | - | 0.0000 | F1 0.0000 | - |
| Random at prevalence | 5.17 | 0.0517 | 0.0517 | F1 0.0517 | analytic, not a run |

Sources: `oscd_results_v2.json` for the per-city counts;
`oscd_evidence.json` for pooled values, random baseline and bootstrap intervals
(seed 0, 10,000 resamples, percentile 2.5-97.5). The Otsu score is overall
accuracy, not F1; its F1 CI is shown separately. The intervals resample the ten
cities only and do not include training or threshold-selection uncertainty.

Disclosure on slide: the test cities had been scored before the reported run.
Source: `PAPER_NOTES.md`, `docs/paper/DRAFT_CORRECTION_LOG.md`, paper abstract
and limitations. The deck must not call this an independent test.

"CNN joint percentile" is the preprocessing chosen on training cities. The
"zero-shot" label applies to the weights only.

## Slide 8 - City variation

| Claim on slide | Value | Source |
|---|---:|---|
| Percentile F1 range | 0.0005 (saclay_w) to 0.2481 (chongqing) | v2 JSON |
| Hardcoded F1 range | 0.0032 (dubai) to 0.3102 (chongqing) | v2 JSON |
| Random-at-prevalence F1 | 0.0517 | `oscd_evidence.json` baselines; analytic |
| CNN zero predictions | 8 of 10 cities (joint percentile) | `oscd_evidence.json` failure counts; v2 JSON |

The chart shows two spectral rules per city. It does not show Otsu or the CNN.
The dotted random line is an expectation, not a scored run.

## Slide 9 - Interpretation

| Claim on slide | Basis |
|---|---|
| Test the resolution path you will deploy | Consequence of the measured degradation result |
| A native-resolution score does not reveal coarse failure | 87.06% -> 4.41% under the transform |
| Report precision with predicted fraction and prevalence | 99.47% precision with 0.068% predicted |
| Do not treat simple indices as a validated fallback | Both spectral rules under-predict pooled change; Otsu over-predicts |
| The paper does not propose a new detector | Paper title/abstract/contributions |

The slide says "Both spectral rules under-predict; Otsu predicts 67.35%". This is
pooled behaviour. It is not true in every individual city (see slide 8 and
`oscd_evidence.json` `prediction_balance`), so do not generalise it per city.

## Slide 10 - What this does not show

| Claim on slide | Basis |
|---|---|
| One architecture, one training run, no seed variation | `ARTIFACT.md`; paper Sec. III/VI |
| Synthetic degradation only | protocol; paper Sec. III |
| OSCD confounds resolution with sensor, geography and season | paper Sec. VI |
| No SCL in benchmark layout | paper Sec. II/VI |
| Ten cities, previously scored | disclosure in paper and notes |
| Deployed app not validated end to end | `ARTIFACT.md`; paper Sec. II |
| No causal claim about the Sentinel-2 gap | paper conclusion and threats document |
| No priority claim | no verified literature search |
| No operational claim | no deployment validation |

## Slide 11 - Next evidence

These are proposals, not results. No v3 score, fine-tuned model, second
architecture or operator study is reported anywhere in the repository. The slide
says "These are evidence needs, not results."

## Slide 12 - Takeaway

| Claim on slide | Value | Source |
|---|---:|---|
| F1 drop | 87.06% -> 4.41% | CSV |
| Predicted fraction at 10 m | 0.068% | CSV |
| Empty changed images | 924 / 935 | CSV |
| CNN F1 | 0.0007 | v2 JSON |
| Spectral F1 range | 0.078-0.118 | v2 JSON (hardcoded 0.0782, percentile 0.1176) |
| Neither is a validated fallback | supported as a negative result | paper abstract/conclusion |

The repository URL and DOI line is a TODO. Do not replace it with an unverified
URL or a DOI that has not been issued.

## Not claimed on any slide

- That all CNNs fail at 10 m.
- That resolution is the sole cause of the OSCD failure.
- That the spectral rules are a validated or recommended fallback.
- That the CNN was fine-tuned, retrained or evaluated on unseen cities.
- That v3 was run, or that a new score exists.
- Any published baseline, ranking or competitive comparison.
- Any priority or originality claim.
- Any operational accuracy, deployment safety or user-study result.
- That the cited references have been verified.

## Numerical consistency checks

Run before a talk:

```bash
./venv/bin/python scripts/make_slides.py
./venv/bin/python -m pytest -q
```

The generator asserts the headline degradation and OSCD values. The tests assert
the paper-figure/table values. If either fails, do not present the deck.
