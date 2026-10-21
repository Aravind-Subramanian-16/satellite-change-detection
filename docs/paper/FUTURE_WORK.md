# Future work

This file records concrete follow-up work. It is not a claim that any item is
under way or funded. Each item states the evidence that would be needed before
a result could be reported.

Priority key: **P0** = required before a journal claim; **P1** = important
next evaluation; **P2** = longer-term or infrastructure.

## 1. Human-in-the-loop evaluation (P0 for a decision-support claim)

**Question:** do operators find the tool's candidate regions useful, and does
the interface's honesty framing change their behaviour?

**Why it matters:** pixel F1 0.1176 says nothing about review time, precision
at a fixed review budget, or automation bias. The current paper calls the tool
decision support without testing that use.

**Design sketch:**

- Recruit consenting analysts; use a task with a known answer key.
- Present candidate regions from the percentile rule and a random/empty
  baseline; record accept/reject, time-to-decision and whether the analyst
  opens the provenance panel.
- Report precision at a fixed number of reviewed regions (e.g. top 20), review
  time, and inter-rater agreement. Do not report a single "accuracy" for the
  interface.
- Include a condition where the heatmap is labelled as evidence magnitude vs.
  an unlabelled heatmap, to test whether the honesty framing reduces
  over-trust.

**Evidence needed:** ethics/IRB approval, a consented sample, a pre-registered
analysis plan, and stored decisions without personal data. **None of this
exists.**

**Risk if skipped:** the paper can describe the tool but cannot claim it
improves decisions. It currently does not make that claim.

## 2. Labelled agriculture data (P0 before any agriculture accuracy claim)

The agriculture profile uses NDVI/NDMI and season warnings, but has no labelled
evaluation. Single-pair differences confuse harvest, irrigation and seasonal
cycles with damage.

**Needed:**

- A locally appropriate, licensed labelled dataset of crop stress, harvest and
  vegetation loss, with acquisition dates matched to the satellite pairs.
- A pre-registered label ontology (what counts as "damage" vs. "harvest").
- Season-matched negatives and a stratified evaluation by crop type.
- A separate analysis of the mandatory same-season warning: how often would it
  fire, and does it prevent false positives?

**Do not:** reuse OSCD urban labels as a proxy for agriculture. Do not report
the urban F1 as an agriculture score.

## 3. Labelled deforestation data (P0 before any deforestation accuracy claim)

The deforestation profile uses NBR/NDVI drops restricted to vegetated
before-pixels, with a 0.5 ha MMU. It is unvalidated.

**Needed:**

- Reference polygons from a national forest-monitoring programme or an
  independent interpreter, with a licence that permits evaluation.
- A definition of forest loss that matches the profile (not all vegetation
  change).
- Seasonal and cloud-matched pairs; the region must have enough clear
  observations for the MMU to be meaningful.
- A stratified evaluation by forest type and patch size, including small
  patches below the MMU.

**Do not:** claim that NBR is validated because it is a standard index; the
threshold and MMU are not.

## 4. Higher-resolution road validation (P1)

At 10 m, roads narrower than roughly 20 m are sub-pixel; the tool's road
profile only reports context and explicitly does not detect roads.

**Needed:**

- Sub-metre or 1–2 m imagery with centreline or road-surface labels.
- A separate detector/segmentation method suited to the resolution; the
  current spectral rules are not adequate.
- Buffer-based metrics (recall within 5/10 m of a mapped road) and a
  comparison to OSM completeness, not just pixel F1.
- A licence review for the high-resolution imagery and OSM ODbL attribution.

**Do not:** present the OSM "changed area near roads" statistic as road
detection.

## 5. Finish the D2 evaluation chain (P0/P1)

The components exist but have no real validation log.

1. **Run the learned classifier notebook.** Requirements: OSCD training cities,
   no test cities, seed 42. Output: joblib metadata with 11 fit cities,
   3 held-out training cities, threshold, `test_split_scored: false`, and a
   pasted validation summary. Until then, no learned accuracy number.
2. **Run the auto-improvement notebook.** Requirements: 12 fixed systems,
   14 leave-one-city-out folds, hard budget, checkpointed log. Output:
   `auto_improve_log.json`/`.md` with failures, per-city variance and the
   component `kept`/`dropped` decisions. Do not add candidates after seeing
   validation results.
3. **Calibrate on held-out training cities.** Report ECE and reliability
   diagrams from `uncertainty.py`; do not call the heatmap a probability.
   Calibration on test cities would be a new test-scoring event and is not
   permitted by the protocol.
4. **CNN fine-tuning.** Run `finetune_cnn.py` only if compute is available; it
   must write a new checkpoint and never touch `best_model.pt`/`model.onnx`.
   Report held-out training metrics, not test metrics, unless the v3 protocol
   explicitly covers the model.
5. **v3 one-shot scoring.** Only after the frozen inputs in
   `PREREGISTRATION.md` exist and a protocol-compliant scorer has been written
   and tested **before** test access. Run once, never tune, report negative
   results and per-city variance. No v3 result exists now.

**Risk:** running any of these on the test split before freezing constitutes
another scoring event and invalidates the one-shot claim.

## 6. Evaluation infrastructure (P1)

- **Independent test set.** A genuinely held-out city set, never used for
  threshold selection or prior scoring, with the same label ontology. Report
  city-level bootstrap intervals; ten cities is too few for narrow intervals.
- **Multi-sensor matrix.** Evaluate on Sentinel-1 SAR, Landsat and higher-
  resolution optical data to test whether the spectral rules and the CNN
  failure generalise. Add sensor-specific preprocessing and report each cell.
- **Seasonal stratification.** Report per-season and per-biome results rather
  than a single pooled number.
- **Published baseline comparison.** Implement at least one published OSCD
  method under the same split/metric protocol, with a verified citation and
  code. Do not quote numbers from incompatible protocols.
- **Cloud-mask evaluation.** A benchmark variant that preserves SCL (or an
  independent cloud mask) so masking quality can be measured, not assumed.

## 7. Operational hardening (P1 for any public deployment)

- Add authentication/authorisation before exposing `/history` or analysis
  endpoints beyond a trusted network.
- Add a retention/deletion policy for previews and AOIs; SQLite history
  currently persists locations.
- Move rate limiting to a shared store if more than one process/instance is
  used.
- Add structured audit logs with access control, not just request IDs.
- Build and test the Docker image; verify non-root execution, health checks and
  PDF export in the container.
- Confirm the GitHub Actions workflow result on a real push; the HTTP/1.1 push
  succeeded through `e8b6678`, but CI has not been checked from this checkout.
- Consider a queue/worker for long analyses instead of in-process work.

**Do not:** publish the demo URL without authentication, monitoring and a
privacy review.

## 8. Paper and evidence (P0 before submission)

- Replace all `[CITE: topic]` placeholders with verified references; write the
  related-work section.
- Verify the OSCD, Copernicus and OSM licences; add a code `LICENSE`.
- Compile the PDF with IEEEtran and check page limits, figure legibility and
  table widths.
- Add author metadata, contributions, COI/funding and AI-assistance disclosure.
- Complete an external novelty search; no priority claim is permitted until
  then.
- Add an independent review of the numbers against the JSON.
- Decide the venue and whether a preprint is appropriate.

## 9. Deliberately not planned

- Another tuning pass on the same ten test cities. This would add another
  scoring event without adding independent evidence.
- Replacing the CNN result with overall accuracy to make it look better. The
  near-empty prediction is the finding.
- Reporting non-urban profile accuracy without labels.
- Describing the pre-registration as an improvement before v3 is run.
- Using the learned classifier or fusion in the default pipeline before they
  have a real validation log.

## 10. Dependency summary

| Item | Depends on | Blocking for |
|---|---|---|
| Human-feedback study | ethics approval, participants, answer key | decision-support usefulness claim |
| Agriculture labels | licensed seasonal labels | agriculture accuracy claim |
| Deforestation labels | licensed reference polygons | deforestation accuracy claim |
| Road validation | sub-metre imagery/centre lines | road detection claim |
| Learned classifier | OSCD training data + Colab run | learned-model accuracy |
| Auto-improvement | 14 train cities + Colab run | v3 S1 system |
| Calibration | held-out train predictions | probability/uncertainty claim |
| v3 | frozen log/artifacts + scorer | one-shot test claim |
| Journal submission | citations, licence, PDF, independent review | publication |
| Public demo | auth, retention policy, monitoring | safe deployment |
