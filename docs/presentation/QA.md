# Q&A for the 10-minute talk

Twenty likely questions with answers that stay inside the saved evidence. The
paper is a single-checkpoint case study, not a competitive benchmark paper.
Answer with the limitation before defending the result when the evidence is weak.

**Ground rules**

- Quote only values in `degradation_results.csv`,
  `benchmarks/results/oscd_results_v2.json` or `oscd_evidence.json`.
- Say "not measured" or "unverified" when the artifact is absent.
- Do not invent a published baseline, DOI, v3 score, fine-tuned result or
  operational accuracy.
- Do not call the OSCD evaluation independent: the ten test cities had been
  scored before the reported run.
- Do not generalise from one checkpoint to "CNNs" as a class.

---

### 1. What is the contribution?

A controlled case study of one frozen CNN under blur and resampling, plus a
zero-shot OSCD evaluation of the same checkpoint and train-selected spectral
reference rules. The useful output is evidence about an evaluation gap and a
reporting pattern: predicted fraction and prevalence next to precision, disclosed
test reuse, and a claim boundary. It is not a new detector and there is no
priority claim.

### 2. Why does F1 collapse so sharply?

Under the controlled transform, F1 falls from 87.06% at 0.5 m to 4.41% at 2 m
and 2.61% at 8-10 m. The decline is recall-dominated: recall falls from 85.36%
to 1.32% while precision rises from 88.82% to 99.47%. The model increasingly
predicts almost no change. The simulation isolates blur and resampling; it does
not establish which real Sentinel-2 differences cause the OSCD result.

### 3. If precision is 99.47%, why is the model bad at 10 m?

Because precision is computed over the few pixels the model predicts. At 10 m it
predicts 91,006 changed pixels out of 134,217,728 (0.068%), and 924 of the 935
changed images receive no predicted change. A nearly empty mask can have high
precision and near-zero recall. Precision without prevalence and predicted
fraction is misleading here.

### 4. Why is the true-change share 5.09% on the degradation chart but 5.17% on OSCD?

They are different datasets. 5.09% is the changed-pixel share in the 10 m
degradation of the 2,048 LEVIR-CD test pairs. 5.17% is the share in the pooled
OSCD v2 test cities. Do not use one as a substitute for the other.

### 5. Why evaluate an aerial-trained CNN on Sentinel-2 at all?

Because that is the frozen checkpoint this project actually has, and the
question is whether its native-resolution score transfers to the resolution and
sensor path a Sentinel-2 user would deploy. The result is negative transfer for
this checkpoint. One checkpoint cannot establish that all CNNs fail on OSCD;
the domain-gap explanation is plausible, not causal.

### 6. Why not fine-tune the CNN on OSCD?

The scope was to evaluate the frozen checkpoint; fine-tuning would create a
different system and would not answer the transfer question. No fine-tuned
result exists in the repository, so none is reported. The paper's conclusion is
about this checkpoint, not about what a properly adapted model could achieve.

### 7. Were the test cities used before?

Yes. The ten official test cities had been scored before the reported v2 run.
An earlier preliminary run with a smaller threshold grid produced pooled F1
0.167 (percentile), 0.104 (hardcoded), 0.095 (Otsu) and 0.0 (CNN). The total
number of scoring events is not recorded. v2 is therefore descriptive, not an
independent test. The paper discloses this and makes no claim of an untouched scoring event.

### 8. How can you report confidence intervals if the test was reused?

The intervals are city-bootstrap intervals over the ten saved per-city
confusion counts: seed 0, 10,000 resamples, percentile 2.5-97.5. They describe
variation across these ten cities only. They do not include training,
threshold-selection or repeated-test uncertainty, and they do not turn the ten
cities into a population sample. The percentile and hardcoded F1 intervals
overlap, and the paired difference interval includes zero, so I do not rank
those two methods.

### 9. Why is there no comparison to published OSCD methods?

I could not implement a published method under the same split, metric and label
handling, and I will not quote a number from an incompatible protocol. The
comparison table in `docs/paper/POSITIONING.md` is deliberately empty; every
cell reads "TODO - fill from original paper." The reference list is also
unverified. A verified baseline comparison is a submission task, not a result.

### 10. Why use overall accuracy for Otsu instead of F1?

Otsu predicts 67.35% of pooled pixels as changed against 5.17% true change. Its
overall accuracy, 0.3439, shows how badly that over-prediction behaves on the
majority class; its F1 is 0.0953. Reporting only F1 would hide the
over-prediction; reporting OA as if it were comparable to the other methods'
F1 would also be misleading. The table labels the score column per method and
shows Otsu's F1 interval separately.

### 11. Is v3 run? Does it fix the test reuse?

No. v3 has not been run and no v3 score exists. The repository has no
protocol-compliant v3 scorer and no v3 output. The file
`docs/paper/PREREGISTRATION.md` was written after earlier scoring, so I do not
present it as evidence of pre-registration or as strengthening the result. A
future v3 would have to be scored once on an untouched set with no re-selection.

### 12. Why only one architecture and one training run?

That is the scope of the case study, and it is the main limit. The training seed
is not recorded, and no seed variation, second architecture or retraining was
run. So the result characterises one checkpoint; it does not estimate
architecture-level or training-level variance. A multi-seed, multi-architecture
study is listed as required evidence, not as completed work.

### 13. Why stop at 10 m? What about 20 m Sentinel-2 bands?

10 m is the finest Sentinel-2 band and the grid used in this evaluation. The
degradation factors stop at 10 m; a 20 m evaluation was not run. I will not
extrapolate the 10 m number to 20 m or to the 20 m bands. That is a separate
experiment.

### 14. Are NDVI/NDBI a usable fallback for the app?

Not on this evidence. The pooled spectral F1 values are 0.0782 (hardcoded) and
0.1176 (percentile). They are above the analytic random-at-prevalence reference
of 0.0517, but that is a very low bar: the rules under-predict change and vary
widely by city, and Otsu over-predicts. The paper does not establish any spectral
rule as a validated fallback. The app withholds accuracy figures for profiles
that are not validated.

### 15. Did you evaluate cloud masking or SCL?

No. The offline OSCD benchmark layout does not include SCL, so cloud and shadow
masking are not evaluated by these scores. The deployed app has an SCL-based
masking path, but that path is not validated end to end by this paper. Any cloud
mask accuracy claim would be unsupported.

### 16. Is the deployed application validated?

No. The paper describes the implementation only to explain the context; it is
not an end-to-end validation of the service. The UI, scene selection, exports
and operational use were not evaluated in a user study or against independent
reference data. The deck says this on slide 10.

### 17. Can this be deployed publicly as-is?

Not safely. The repository documents the prototype's limits, including
authentication, retention and rate-limit concerns. This talk does not claim
operational readiness, uptime, security or fitness for decisions. A public
deployment would need a separate engineering and legal review.

### 18. What about licences and data redistribution?

OSCD labels are reported as CC BY-NC-SA in this project; the licence must be
verified at the official source, and the non-commercial clause may restrict
commercial use. Copernicus Sentinel data and OSM/Overpass have their own terms.
The repository does not redistribute OSCD imagery or labels. No code licence has
been chosen; that is an owner decision and a submission blocker. Legal review is
required before redistribution or commercial use.

### 19. What would change the conclusion?

An untouched city set or new dataset; a second architecture and checkpoint with
multiple seeds; real same-scene acquisitions at multiple resolutions; an
SCL-preserving benchmark; a wider threshold grid; and an operator study on
whether warnings change decisions. Another score on the same ten cities would
not make the evaluation independent.

### 20. Why present a negative result?

Because an 87% native-resolution score can hide near-empty predictions on the
resolution path a user actually deploys. The paper makes that risk measurable
and states what is not supported. It is not a competitive-score paper, and a
venue that requires a higher benchmark number is not the right fit. The
contribution is the evidence and the reporting discipline, not a detector.

---

## If you do not know

Say this, then stop:

> "That is not in the saved results. I can point you to the file that would
> answer it, or mark it as unverified. I will not estimate it on the spot."

Then do one of three things:

1. Name the missing artifact, for example: "A published OSCD baseline would
   require a verified implementation and citation; the comparison table is
   still empty."
2. Name the file that does contain the answer, for example:
   "The per-city counts are in `oscd_results_v2.json`; I can walk through the
   saved row."
3. Offer to follow up after checking, without promising a number.

Do not guess a DOI, a baseline, a v3 score, a training seed, a licence, a
fine-tuned result or an operational metric. Do not average city scores on the
spot. Do not call the study independent, and do not describe the app as
validated.

## Quick numbers

| Item | Value |
|---|---:|
| LEVIR-CD test pairs | 2,048 |
| F1 at 0.5 / 1 / 2 / 8-10 m | 87.06 / 70.81 / 4.41 / 2.61% |
| Recall at 0.5 / 10 m | 85.36 / 1.32% |
| Precision at 0.5 / 10 m | 88.82 / 99.47% |
| Predicted changed at 10 m | 0.068% (91,006 / 134,217,728) |
| Changed images empty at 10 m | 924 / 935 (98.82%) |
| OSCD pooled pixels | 3,077,936 |
| OSCD true change | 5.17% |
| Hardcoded / percentile F1 | 0.0782 / 0.1176 |
| Otsu OA / F1 | 0.3439 / 0.0953 |
| CNN joint / reflectance F1 | 0.0007 / 0.0000 |
| Random at prevalence F1 | 0.0517 (analytic) |
| CNN zero-prediction cities | 8 of 10 |
