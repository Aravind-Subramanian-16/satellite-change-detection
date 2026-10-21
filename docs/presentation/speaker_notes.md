# Speaker notes - 10-minute talk

Generated from the notes embedded in `slides.pptx`. Edit the generator,
not this file, so the deck and script stay in sync.

Speaking budget: **9:45** plus **0:15** buffer. The script is **1253 words**, about **9.6 minutes** at 130 words per minute. Rehearse with a timer; do not speed up to fit.

## Timing

| Slide | Topic | Target | Words | Cumulative |
|---:|---|---:|---:|---:|
| 1 | Title and roadmap | 0:25 | 107 | 0:25 |
| 2 | Why resolution is the problem | 0:50 | 124 | 1:15 |
| 3 | Design: one checkpoint, two evaluations | 0:45 | 97 | 2:00 |
| 4 | Degradation protocol | 0:55 | 114 | 2:55 |
| 5 | F1 versus resolution | 0:55 | 107 | 3:50 |
| 6 | Why precision misleads | 0:50 | 91 | 4:40 |
| 7 | Real Sentinel-2 (OSCD) results | 1:10 | 126 | 5:50 |
| 8 | City-level variation | 0:50 | 94 | 6:40 |
| 9 | Practical interpretation | 0:55 | 104 | 7:35 |
| 10 | What this does not show | 0:50 | 106 | 8:25 |
| 11 | What evidence would strengthen it | 0:40 | 89 | 9:05 |
| 12 | Takeaway | 0:40 | 94 | 9:45 |

If you are behind after slide 6, compress slides 8 and 11 to one sentence
each. Never cut the repeated-test disclosure on slide 7 or the claim
boundary on slide 10. If you are ahead, stop; do not add results.

## Script

### Slide 1 - Title and roadmap (25 s)

Good morning. My talk is about a failure mode that aggregate benchmark scores hide: a change detector that looks strong at half a metre and almost stops detecting by two metres. This is a case study of one frozen checkpoint, not a new model, and not a claim that all CNNs fail. I will show a controlled degradation experiment on 2,048 aerial test pairs, a transfer evaluation on ten Sentinel-2 cities, and the limits of both. The question is narrow: what happens to a validated score when the input resolution changes? Please hold two questions: what is actually validated here, and what evidence would change the conclusion?

### Slide 2 - Why resolution is the problem (50 s)

The starting point is a mismatch of pixel support. The checkpoint was trained and scored on LEVIR-CD, which is half-metre aerial imagery. Sentinel-2 gives us ten-metre and twenty-metre bands, free and frequently revisited. Ten metres is twenty times coarser per side than half a metre, and four hundred times the area. On this diagram, the large square is one Sentinel-2 pixel; the orange square is one LEVIR-CD pixel, drawn to scale. At that size, small buildings, road edges and boundaries become sub-pixel or mixed. That is not a cosmetic difference. The question is whether a model validated on the fine grid still works when the input is coarsened. The paper does not assume the answer; it measures the same checkpoint under a controlled transform.

### Slide 3 - Design: one checkpoint, two evaluations (45 s)

Here is the design. Two evaluations, one frozen checkpoint, no retraining. On the left, the 2,048 LEVIR-CD test pairs at six factors from one to twenty. On the right, the ten official OSCD test cities: 3,077,936 pixels, 5.17 percent labelled change. The CNN weights are zero-shot on OSCD; the spectral rules are train-selected reference points, not a proposed solution. One architecture, one training run, threshold fixed at 0.5 throughout. That scope is deliberate. This is a case study of a deployed checkpoint, not an architecture comparison, and I will not generalise from one model to all CNNs.

### Slide 4 - Degradation protocol (55 s)

The degradation protocol is simple and reproducible. Start with a 256 by 256 pair. Blur with a Gaussian whose radius is the factor divided by two. Downsample with LANCZOS to 256 over the factor, squared. Upsample back to 256. At factor twenty, the intermediate is only twelve by twelve pixels. Factors one, two, four, eight, sixteen and twenty map to half a metre through ten metres. Then ImageNet normalization, a fixed 0.5 threshold, and pooled true positives, false positives and false negatives over all 2,048 pairs. The blur and resampling isolate the effect of pixel support. They do not simulate Sentinel-2 spectra, atmosphere, mixed-pixel physics or noise. I will come back to that distinction.

### Slide 5 - F1 versus resolution (55 s)

Here is the main result. At half a metre, pooled F1 is 87.06 percent. At one metre it is 70.81, a drop of 16.25 points. At two metres it is 4.41 percent. From eight to ten metres it is 2.61. The dashed line is recall: 85.36 percent at native resolution, 57.01 at one metre, 2.26 at two metres, and 1.32 at eight to ten. The decline is recall-dominated. Precision actually rises, from 88.8 percent at native resolution to 99.5 percent at ten metres. So the model is not becoming noisy; it is becoming silent. That is why the next slide matters more than the F1 number alone.

### Slide 6 - Why precision misleads (50 s)

At ten metres the model predicts 91,006 pixels changed out of 134,217,728. That is 0.068 percent. 924 of the 935 images that actually contain change receive no predicted change at all, which is 98.82 percent. Precision is 99.47 percent, but it comes from 90,527 true positives and only 479 false positives. A precision-only summary would call this excellent; a recall or predicted-fraction summary exposes that the mask is almost empty. This is the central reporting lesson: precision is not interpretable without prevalence and predicted fraction. The paper therefore reports all three.

### Slide 7 - Real Sentinel-2 (OSCD) results (70 s)

Now the real Sentinel-2 evaluation. OSCD, ten official test cities, 3,077,936 pixels, 5.17 percent true change. The percentile rule has the best pooled F1 among the spectral rules, 0.1176, with a city-bootstrap interval from 0.054 to 0.180. The hardcoded NDVI/NDBI rule is 0.0782, interval 0.017 to 0.185. Those intervals overlap, and the paired difference interval includes zero, so I do not rank them. Otsu predicts 67.35 percent of pixels changed; its headline is overall accuracy 0.3439, not F1. The CNN is near empty: F1 0.0007 for joint-percentile preprocessing, which was chosen on the training cities, and 0.0000 for reflectance. One disclosure is essential: these ten cities had been scored before the reported run. These are descriptive scores, not an independent test, and the paper says so.

### Slide 8 - City-level variation (50 s)

Pooled numbers hide the city variation. Percentile F1 ranges from 0.0005 in saclay_w to 0.2481 in chongqing. Hardcoded ranges from 0.0032 in dubai to 0.3102 in chongqing. The random-at-prevalence F1 is 0.0517, shown as the dotted line; many city values sit near or below it. The CNN predicts nothing in eight of ten cities. These are descriptive ranges from ten cities. The intervals resample cities or pixels; neither includes training or threshold-selection uncertainty. So the pooled score is a summary, not a stable estimate of how the tool will behave in a new city.

### Slide 9 - Practical interpretation (55 s)

What does this mean in practice? Start with the resolution path you will deploy. A native-resolution benchmark score does not reveal a coarse-resolution failure; if the product runs on ten-metre data, the evaluation should too. Second, report precision with predicted fraction and prevalence. A near-empty mask can look nearly perfect. Third, do not treat simple spectral indices as a validated fallback. The percentile rule is the best of the spectral options here, but it under-predicts change, and Otsu predicts two thirds of pixels as changed. The paper identifies an evaluation risk. It does not explain the real Sentinel-2 gap or propose a new detector.

### Slide 10 - What this does not show (50 s)

The limits matter. One architecture and one training run; no retraining, fine-tuning or seed variation. The degradation is synthetic: no Sentinel-2 spectra, atmosphere, mixed-pixel physics or noise. The OSCD evaluation uses real data, but it confounds resolution with sensor, geography and season, and the benchmark layout has no SCL, so clouds are uncontrolled. Ten cities, and the test split had been scored before the reported run. Finally, the deployed application, its scene selection and its interface are not validated end to end. So: no causal claim about the real Sentinel-2 gap, no priority claim, no operational claim. What remains is descriptive evidence of an evaluation risk.

### Slide 11 - What evidence would strengthen it (40 s)

What would change the conclusion? A second architecture and checkpoint, with multiple seeds. Real acquisitions of the same scenes at multiple resolutions, rather than synthetic resampling. An untouched city set or a new dataset. An SCL-preserving benchmark and a wider threshold grid. And an operator study on whether warnings actually change decisions. These are evidence needs, not results; none of them is in the paper. If you take one thing for your own evaluation practice, prioritise these two: test the deployed path, and do not reuse a test split.

### Slide 12 - Takeaway (40 s)

Takeaway: a half-metre score is not a ten-metre validation. F1 fell from 87.06 to 4.41 percent by two metres under blur and resampling. At ten metres, 0.068 percent of pixels were predicted changed, and 924 of 935 changed images were empty. On real OSCD, the CNN F1 was 0.0007, the spectral rules were 0.078 to 0.118, and neither is a validated fallback. The paper reports these limits explicitly. The evidence is saved, the code and figures are in the artifact, and citations are still being verified. Thank you; I am happy to take questions.

## Delivery notes

- Pause after the 4.41% number on slide 5 and after the 0.068% number
  on slide 6. Those are the two results the audience should retain.
- Say the repeated-test disclosure on slide 7 slowly and without
  qualification. Do not bury it in the limitations slide.
- On slide 2, point to the orange square, not the large blue square.
- Do not improvise a published baseline, a v3 score, a fine-tuned
  result, a causal mechanism or an operational claim. If asked, use
  `QA.md` and name the missing artifact.
- The deck says `Draft` because citations are not yet verified and no
  PDF build exists. Do not remove that label for a public talk.

Q&A: `QA.md`. Demo: `DEMO.md`. Slide-level claim audit:
`CLAIMS_ON_SLIDES.md`. One-page handout: `handout.pdf`.
