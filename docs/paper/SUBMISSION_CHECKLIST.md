# Conference submission checklist

**Current status: NOT READY TO SUBMIT.** This file tracks the current
`paper.tex`; for rationale and scope, see
[`CONFERENCE_READINESS.md`](CONFERENCE_READINESS.md).

## Completed in this checkout

- [x] Recovered saved per-image degradation counts and per-city OSCD confusion
  records from repository history.
- [x] Recomputed pooled degradation metrics and OSCD derived summaries from
  saved counts; regenerated paper tables.
- [x] Separated the current RGB-screening application from the historical
  offline CNN/spectral experiments; no application accuracy is claimed.
- [x] Added a nine-entry bibliography and resolved every citation key. No
  `[CITE: ...]` placeholders remain.
- [x] Disclosed previous scoring of OSCD test cities; no claim of an untouched
  or independent OSCD test is made.
- [x] Updated artifact and reference-verification notes to distinguish saved
  metric derivation from model-inference reproduction.

## Blocking before submission

- [ ] Obtain and independently review the source imagery, labels, exact model
  checkpoint and run metadata if a full rerun is possible. The original
  inference runs cannot be reproduced from the current checkout.
- [ ] Preserve the disclosure of prior OSCD test use. Do not tune or rescore
  those cities as a fresh test; use a separately approved evaluation protocol
  for new model work.
- [ ] Verify every cited statement against the publisher or official source,
  confirm DOI/URL fields, and format references to the selected IEEE venue.
- [x] Compile `docs/paper/paper.tex` with IEEEtran; five-page PDF is at
  `docs/paper/paper.pdf`, and extracted text contains the manuscript and
  bibliography without unresolved citations.
- [ ] Inspect every PDF page, figures, tables and bibliography visually, then
  verify the page limit against the selected IEEE venue. Only the first page
  has been rendered and visually checked; the venue is not yet selected.
- [ ] Select the exact conference, track and deadline; check its current
  submission, anonymization and formatting requirements.
- [ ] Confirm author names/order, affiliation, contact, ORCIDs, funding,
  acknowledgements, conflicts-of-interest and AI-assistance disclosures.
- [ ] Verify OSCD, Copernicus and OpenStreetMap terms; obtain legal review where
  required. No code licence has been chosen.
- [ ] Have an independent reviewer compare manuscript statements with the
  saved evidence and implementation.
- [ ] Confirm data/code availability statements and repository/archive access;
  do not claim a DOI or public release until it exists.
- [ ] Complete the venue-required ethics and dual-use review for the
  environmental decision-support application.

Do not submit based solely on recomputed tables: they verify arithmetic from
saved counts, not the original imagery, predictions, training process or
independent scientific validation.
