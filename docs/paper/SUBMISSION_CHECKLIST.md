# Submission checklist

**Readiness: NOT READY.** The manuscript, figures and audits exist, but the
citations, licence, author metadata, PDF build and independent validation are
unfinished. This checklist is deliberately conservative; do not submit until
every blocking item is resolved.

Status legend: `[x]` done in this checkout, `[ ]` not done, `[!]` owner
decision or external verification required.

## A. Scientific claims and evidence

- [x] Every reported test-set number comes from `benchmarks/results/oscd_results_v2.json`,
  `degradation_results.csv` or the generated tables; the training-only
  leave-one-city-out values come from `oscd_loco_thresholds.json`; no estimated
  or invented value was added.
- [x] The training-only LOCO check is labelled as a robustness check, not a test
  score, and adds no test-scoring event.
- [x] Pooled values were recomputed from confusion counts and match the v2
  Markdown.
- [x] Per-city F1 range (0.0005–0.2481 for percentile) is accurate.
- [x] The CNN result is reported as measured (F1 0.0007 / 0.0000), not tuned
  away or replaced by overall accuracy.
- [x] Otsu's headline is labelled overall accuracy (0.3439), with F1 0.0953
  shown only for completeness and its 67.35% predicted-change rate stated.
- [x] The two prior test-scoring events are disclosed; v2 is not presented as
  independent confirmation.
- [x] The paper says no v3 result exists and does not imply that the
  preregistered protocol improved anything.
- [x] No accuracy number is shown for the learned classifier, fusion,
  compositing, PIF, MMU, morphology or the non-built-up profiles.
- [x] `CLAIMS_AUDIT.md` lists claims with evidence and status.
- [x] `THREATS_TO_VALIDITY.md` covers construct, internal, external,
  statistical, reproducibility and ethical validity.
- [ ] A reviewer independent of the project has checked the manuscript against
  the JSON and the code. This is a **blocking** quality check.
- [ ] Any published OSCD baseline comparison has been added with a verified
  citation and a comparable protocol, or the paper explicitly says none is
  made. (Currently: none is made; `TODO_CITATIONS.md` records the gap.)

## B. Manuscript completeness

- [x] IEEEtran conference class; abstract, introduction, data/task, methods,
  protocol, results, validation-only section, discussion, limitations,
  reproducibility/ethics, conclusion and appendix are present.
- [x] Related-work material exists only as citation placeholders; a real
  related-work section must be written after the citations are verified.
- [ ] Replace every `[CITE: topic]` placeholder with a verified reference and
  add a bibliography (`.bib`) or `thebibliography` block.
- [ ] Add a proper related-work section that positions the work without
  priority language.
- [ ] Add a future-work section covering the human-feedback loop, labelled
  agriculture/deforestation data, higher-resolution road validation and the
  unfinished D2 ideas (some material exists in `CLAIMS_AUDIT.md`, `FUTURE_WORK.md`
  and the discussion; it must be in the manuscript).
- [ ] Fill in the author block, affiliations, corresponding author and ORCIDs.
- [ ] Remove or update the line "Anonymous review version --- do not submit
  as-is" once the submission mode is known.
- [ ] Check the paper against the venue's page limit; the current two-column
  manuscript plus a 50-row longtable may exceed a short conference limit.
- [ ] Proofread for hyphenation, table widths, figure resolution and caption
  consistency.
- [ ] Compile the PDF twice and inspect it. **Not done:** no LaTeX engine on
  this host.
- [ ] Check that all `\input` files exist and are the generated versions.
- [ ] Confirm no forbidden wording ("first", "novel", "state of the art",
  "outperforms") survived the edits. A mechanical scan is recommended.
- [ ] Add line numbers or page numbers if the venue requires them.
- [ ] Check reference style and that no citation is a placeholder URL only.

## C. Anonymisation and metadata

- [ ] Decide whether the venue is double-blind. If yes:
  - remove author names, affiliations, acknowledgements and funding;
  - remove or anonymise the GitHub URL in the manuscript and supplement;
  - ensure the repository/Drive links do not identify the authors;
  - check PDF metadata and file names.
- [ ] If not double-blind, add the author block, affiliation and contact.
- [ ] Add acknowledgements only for real, confirmed contributions/funding.
- [ ] Add a conflict-of-interest statement (none known, but owner must confirm).
- [ ] Add a funding statement or "no specific funding" as appropriate.
- [ ] Confirm that no credential, API key, Drive path or personal email is in
  the manuscript, figures, logs or supplement.

## D. Data and code availability

- [x] Code, tests, figure generator and audits are in the repository.
- [x] The v2 JSON/Markdown source of record is tracked.
- [x] The paper states that OSCD imagery/labels and model weights are not
  redistributed.
- [ ] Publish the repository or prepare an anonymised archive; verify the link
  works from a logged-out browser.
- [ ] Add a `LICENSE` file for the code. **No licence file currently exists.**
  The owner must choose one and check dependency compatibility.
- [ ] Add a data-availability statement naming OSCD, its official access route
  and the fact that the checkpoint is not included.
- [ ] Add a code-availability statement with the exact commit/tag used for the
  paper. The paper names `a6dad9e`; confirm the tag/commit persists in the
  public repository.
- [ ] Decide whether to deposit the v2 JSON/Markdown and figure manifest in a
  DOI-granting archive (e.g. Zenodo). If yes, verify the deposit licence and
  metadata. Do not claim a DOI until it exists.
- [ ] Include the v2 JSON hash in the supplement or availability statement.
- [ ] Confirm that no OSCD imagery, labels, joblib or weight file is committed.
- [ ] Confirm that no `.env` file or credential is in the repository history.

## E. Licences and intellectual property

- [x] `docs/LIMITATIONS.md` records OSCD CC BY-NC-SA, Copernicus terms and OSM
  ODbL as understood in this project.
- [ ] Verify the current OSCD licence at the official source. The non-commercial
  clause may prohibit commercial use of the data or derived labels; confirm
  whether the paper's figures/tables are permitted.
- [ ] Verify the Copernicus Data Space terms for the live tool and any cached
  data.
- [ ] Verify OpenStreetMap tile/Overpass usage against the current tile policy
  and ODbL attribution requirements.
- [ ] Confirm that the CNN checkpoint's training-data licence permits this use
  and evaluation. Its provenance is owner-supplied and unverified here.
- [ ] Confirm that the code licence is compatible with all dependencies
  (FastAPI, Leaflet, scikit-learn, reportlab, etc.).
- [ ] Confirm that figures generated from OSCD-derived labels may be
  redistributed; if not, replace them with non-derivative plots or obtain
  permission.
- [ ] Legal review before any commercial deployment or redistribution. The
  paper's non-commercial dataset use is a **blocking** item for a commercial
  venue or product claim.

## F. Ethics, dual use and privacy

- [x] The paper states the tool is for civil decision support, not targeting or
  enforcement, and requires human verification.
- [x] `docs/LIMITATIONS.md` documents the lack of authentication and the local
  history/privacy risk.
- [ ] Add an explicit ethics statement if the venue requires one: no human
  subjects, no personal data collected by the benchmark, but AOI/history data
  exists in the app.
- [ ] Complete a dual-use review with the owner/institution. Change detection
  is dual-use; the paper must not enable targeting or surveillance.
- [ ] Confirm that no example AOI or screenshot reveals a sensitive location.
- [ ] State that the tool has no authentication and must not be deployed
  publicly without an authenticated proxy and data-retention policy.
- [ ] Decide whether to include the live demo URL; if yes, ensure it is
  rate-limited, monitored and does not expose history.
- [ ] Add a data-retention/deletion statement for the app's SQLite history if
  the demo is public.

## G. Authorship, contributions, COI and AI disclosure

- [ ] Agree the author list and order with all authors.
- [ ] Write a contributions statement (e.g. CRediT) that reflects actual work.
  Do not invent roles. Placeholder:
  - AUTHOR_1: conceptualisation, software, validation, writing — confirm;
  - AUTHOR_2: supervision, review — confirm;
  - add/remove as appropriate.
- [ ] Obtain approval from every author for the submitted version.
- [ ] Confirm no undisclosed conflict of interest.
- [ ] Disclose AI assistance according to the venue policy. This project used
  an AI coding assistant for code, tests, analysis, documentation and drafting;
  the human owner is responsible for verifying all content. Do not conceal
  this if the venue requires disclosure.
- [ ] Confirm that AI assistance does not violate the venue's authorship policy
  (AI tools are not authors).
- [ ] Check whether the venue requires a data/code provenance statement for
  AI-generated content.

## H. Preprint / arXiv decision

- [ ] Decide whether to post a preprint. Consider:
  - the double-blind policy of the target venue;
  - co-author/employer/funder approval;
  - the dataset licence (do not repost OSCD data);
  - the fact that a preprint is not peer review;
  - the permanence of the posting.
- [ ] If posting, choose the licence deliberately and verify the arXiv category
  (cs.CV / eess.IV / cs.SE) and endorsement requirements.
- [ ] Do not describe the preprint or repository as "published" or "validated".
- [ ] Record the preprint DOI/URL only after it exists.

## I. Venue-specific preparation

- [ ] Choose the venue (see `VENUES.md`); record the decision and date.
- [ ] Download and read the current author guidelines; record page limit,
  format, anonymity, supplementary-material rules and fee/APC.
- [ ] Check whether the venue accepts negative results or benchmark papers.
- [ ] Check whether a workshop is archival; state this in the CV/record.
- [ ] Check the submission system's file-size and figure-format limits.
- [ ] Check whether a cover letter is required. If so, write one that states
  the negative result and the uncomputed v3 plainly.
- [ ] Check whether the venue requires a reproducibility checklist or artifact
  appendix; fill it truthfully.
- [ ] Check whether the venue requires a lay summary or impact statement.

## J. Final technical checks

- [x] `./venv/bin/python -m pytest -q` passes with the recorded counts.
  Evidence (2026-10-21): **137 passed, 3 skipped, 1 warning** (runtime varies);
  skips are `rasterio` absent, `torch` absent and the missing dataset sample. The
  timing varies; the pass/skip counts are the claim.
- [ ] `python scripts/make_paper_figures.py` regenerates figures without
  errors and the manifest hash matches the v2 source.
- [ ] Verify every figure embedded in the PDF is the latest generated version
  (check file timestamps/manifest).
- [ ] Verify table numbers and captions against the JSON one last time.
- [ ] Verify that the appendix longtable does not break the page limit.
- [ ] Check colour-blind safety and grayscale legibility of figures.
- [ ] Check that all fonts are embedded and images are at least 300 dpi where
  required.
- [ ] Run a spell-check and a link check.
- [ ] Remove temporary files, cached results and personal paths from the
  supplement.
- [ ] Archive the exact submission bundle and record its SHA-256.

## K. Submission-day record

- [ ] Venue and track:
- [ ] Submission date (UTC):
- [ ] Manuscript title:
- [ ] Author list as submitted:
- [ ] Anonymised? yes/no:
- [ ] Code commit/tag:
- [ ] v2 JSON hash:
- [ ] PDF SHA-256:
- [ ] Supplementary bundle SHA-256:
- [ ] AI-assistance disclosure included? yes/no:
- [ ] Confirmation number:
- [ ] Decision deadline (if stated):
- [ ] Owner sign-off:

## L. After submission

- [ ] Do not run v3 or tune on the test split while under review unless the
  venue and preregistration explicitly allow it and the event is disclosed.
- [ ] Record reviewer comments and responses verbatim.
- [ ] If revisions require new experiments, preregister them before running and
  disclose any test-split use.
- [ ] Update `CLAIMS_AUDIT.md`, `PROGRESS.md` and the paper from saved JSON, not
  from memory.
- [ ] If rejected, do not shop the same claims to a venue with a lower bar
  without addressing the validity threats.

## Blocking items (must be resolved first)

1. No verified citations or bibliography; related work is placeholders.
2. No code `LICENSE`; dataset/checkpoint licence review incomplete.
3. No compiled PDF; page count and layout unverified.
4. No independent validation or v3 result; the paper is a descriptive negative
   result, and the venue must accept that scope.
5. Author list, contributions, COI, funding and AI disclosure are blank.
6. Repository access/anonymisation decision is unresolved.
7. External novelty verification is incomplete; no priority claim is allowed.

**Submission is blocked until items 1–7 are closed.**
