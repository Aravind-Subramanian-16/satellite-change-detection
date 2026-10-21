# Reviewer objections and prepared responses

Twelve objections a careful reviewer could raise about the current manuscript,
with the response the evidence supports. Each response points to the paper or a
tracked file. None of these responses adds a new result.

The short version: the paper is a descriptive case study with a disclosed,
previously used test split and one architecture. It does not claim a new
method, a competitive score, or a validated replacement for the CNN.

## 1. “This is a negative result with no methodological contribution.”

**Response.** Correct: the paper does not propose a new detector. It reports a
controlled degradation study and a zero-shot Sentinel-2 evaluation of one frozen
checkpoint, with the full protocol and the scoring history disclosed. The
useful findings are the size and shape of the collapse (F1 87.06% at 0.5 m,
70.81% at 1 m, 4.41% at 2 m, 2.61% at 8–10 m), the near-empty coarse
predictions (0.068% of pixels predicted changed at 10 m; 924 of 935 changed
images receive no prediction), and the weak spectral reference points. A
practitioner who reads only native-resolution benchmark scores would not see
that risk.

**Residual risk.** A venue that requires a new method may reject on scope. The
paper should target a workshop, software, or empirical-evaluation venue. Do not
add a “new method” claim to compensate.

## 2. “Only one architecture and one training run. How can you generalise?”

**Response.** We do not generalise. The abstract, Sec. IV-A and Sec. VII state
that one MobileNetV2-based Siamese U-Net, one training run and one frozen
checkpoint were tested, with no retraining, fine-tuning, seed variation or
architecture comparison. The claim is about this checkpoint under this
protocol, not about “CNNs” as a class. The OSCD result is likewise one
checkpoint with two preprocessing variants.

**Residual risk.** A second architecture could collapse at a different
resolution or recover at 2 m. That would not erase this measurement, but it
would limit its transfer. A multi-architecture, multi-seed study is future work.

## 3. “Blur and resampling are not Sentinel-2. Your resolution experiment is artificial.”

**Response.** Agreed, and the paper says so in Sec. IV-A and Sec. VII. The
degradation experiment holds scene content fixed and varies only blur and
sampling; it is not a sensor simulation. It deliberately omits Sentinel-2
spectral bands, radiometric calibration, atmospheric correction, mixed-pixel
composition and sensor noise. The separate OSCD evaluation uses real
Sentinel-2 data but confounds resolution with those other differences. The two
experiments answer different questions; neither is presented as the other.

**Residual risk.** There is no real multi-resolution acquisition of the same
LEVIR-CD scenes. A reviewer may still ask for one; that would be a new data
collection, not a re-analysis of the saved results.

## 4. “The collapse between 1 m and 2 m looks like a bug or a preprocessing artifact.”

**Response.** The implementation is short and inspectable:
`evaluate_degradation.py` applies `GaussianBlur(radius=factor/2)`, LANCZOS
downsampling to `(256/f)×(256/f)` and LANCZOS upsampling back to 256×256, then
ImageNet normalisation and a 0.5 threshold. The 2 m level is a 128×128
intermediate; 4 m is 64×64; 10 m is 12×12. The saved per-image counts show a
recall collapse (57.01% at 1 m to 2.26% at 2 m), not a rise in false positives.
The paper describes this as consistent with information loss but does not claim
a mechanism.

**Residual risk.** The checkpoint and imagery are absent here, so no independent
rerun was possible. We invite a code review of `evaluate_degradation.py` and a
rerun when the artefacts are available. Do not claim the cause is proven.

## 5. “Precision stays around 99% at coarse resolution. That contradicts ‘collapse’.”

**Response.** Precision is high because the model predicts almost nothing. At
10 m it predicts 91,006 of 134,217,728 pixels changed (0.068%) against
6,837,404 changed ground-truth pixels. F1 and recall collapse; 924 of 935
changed images receive no predicted change. The paper reports precision next to
predicted fraction and true prevalence, and states explicitly that high
precision here describes how little the model predicts, not how well it
localises change.

**Residual risk.** A reader who quotes precision alone can still be misled.
Every slide and abstract sentence should keep the predicted-fraction context.

## 6. “The OSCD test cities were already scored. Your evaluation is contaminated.”

**Response.** Disclosed in the abstract, Sec. V-A and Sec. VII. The ten official
test cities had been scored before the reported v2 run; an earlier preliminary
run with a smaller grid produced pooled F1 values of 0.167 (percentile), 0.104
(hardcoded), 0.095 (Otsu) and 0.0 (CNN). The total number of scoring events is
not recorded. The v2 run re-evaluated those cities after the configuration was
fixed on training cities, so it is not an independent test of unseen cities.
The paper presents descriptive scores, not an unbiased generalisation estimate.

**Residual risk.** No analysis of existing data can restore independence. A
genuinely untouched city set or a new dataset is required; until then, do not
say “confirmed,” “unseen” or “held-out” about these ten cities.

## 7. “Ten cities is too few, and your intervals are narrower than the real uncertainty.”

**Response.** The pooled intervals resample the ten cities (seed 0, 10,000
resamples), so their width reflects city sampling only. Per-city intervals use a
pixel-bootstrap approximation and ignore spatial correlation. Neither includes
training or threshold-selection uncertainty, and no interval is reported for
overall accuracy. The paper states all of this in Sec. V-C and Sec. VII. The
paired percentile-minus-hardcoded difference has interval −0.0176 to +0.0778,
which includes zero, so the paper does not rank the two rules.

**Residual risk.** Even the city-level intervals may be optimistic because the
cities are not a random sample and there are only ten. Treat them as
descriptive, not as coverage guarantees.

## 8. “The spectral rules are strawmen. Where are the published baselines?”

**Response.** The rules are deliberately simple, train-selected reference points,
not a claim about the best available spectral method. The paper says they are
transparent but weak: hardcoded NDVI/NDBI reaches pooled F1 0.0782 and
percentile 0.1176, and only the percentile interval lies entirely above the
random-at-prevalence F1 of 0.0517. They are included because they are
inspectable and because the frozen CNN performs far worse. No published OSCD score is quoted, because
no bibliography or comparable protocol has been verified.

**Residual risk.** A tuned or learned spectral baseline could perform better and
change the practical conclusion. The paper does not claim otherwise. Add
published baselines only after verifying the original papers and matching
split/metric definitions.

## 9. “Otsu’s overall accuracy of 0.3439 is bizarre. Why report it at all?”

**Response.** Otsu predicts 67.35% of pixels changed, far above the 5.17% true
prevalence, so its F1 is not a useful standalone summary. The paper reports its
full confusion-derived metrics and uses overall accuracy as its headline, with
a caption that says so. Otsu is an unsupervised threshold reference, not a
recommended method. Its high recall (0.6684) is bought with precision 0.0513.

**Residual risk.** Mixing OA and F1 across rows can confuse a reader. The table
labels the OA column and the caption explains the choice; do not quote 0.3439
as if it were comparable to F1.

## 10. “Your thresholds sit at grid edges, and the selection log is incomplete.”

**Response.** Both hardcoded thresholds (NDVI drop 0.30, NDBI rise 0.30) lie at
the edges of the search grid, so the selected rule may be limited by the grid
rather than by the data. The percentile choice (99.0) is interior. The code
selects on the 14 training cities, and no test labels were used to fit the v2
thresholds, but the full selection log and the CNN’s training scores are not
retained. The paper describes the train-only separation as documented, not as
fully audited.

**Residual risk.** A wider pre-registered grid could change the hardcoded score.
Do not describe the selected values as optimal.

## 11. “No cloud/shadow masking and no end-to-end validation of the app.”

**Response.** The benchmark layout does not include the Sentinel-2 Scene
Classification Layer, so cloud and shadow exclusion is not evaluated and cloud
effects are uncontrolled. The system-overview section describes implementation
facts (upload path, catalogue query, scene ranking, SCL masking, index
differences); it is explicitly not an end-to-end validation of the deployed
service. The benchmark also does not exercise scene selection, upload handling,
the user interface or report generation.

**Residual risk.** Real deployments face clouds, season and scene-selection
errors that these scores do not measure. The paper should keep the
“decision-support prototype” framing.

## 12. “This is not submission-ready: data and weights are absent, citations are placeholders, and there is no PDF.”

**Response.** Correct. The artefact guide records the exact commands, saved
inputs and hashes, and lists what is missing. The manuscript uses deliberate
`[CITE: ...]` slots because no reference metadata has been verified; it must not
be submitted in this state. No PDF was built because no LaTeX engine is
available on this host; the owner must compile on Overleaf and check the
four-page limit excluding references. The paper makes no claim that these
blockers are resolved.

**Residual risk.** Acceptance is blocked until the owner replaces every citation
slot, verifies the bibliography, compiles the PDF, supplies the artefacts if
requested, and completes the licence review. Do not fabricate any of these.

## Do not say

- Any priority or originality claim.
- “Best in class” or a comparison with published OSCD scores.
- “Resolution causes the OSCD failure.” The OSCD evaluation confounds factors.
- “The spectral rules are a validated alternative.” Both under-predict change.
- “The test cities are held out / unseen.” They had been scored before v2.
- “The CNN achieves 94.83% accuracy.” That is the all-no-change rate.
- “Precision is 99%, so the coarse model still works.” It predicts almost
  nothing.
- “The app is validated.” Only the offline benchmark was evaluated.
