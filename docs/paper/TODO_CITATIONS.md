# Reference verification status

As of 2026-10-22, `paper.tex` contains nine bibliography entries and no
`[CITE: ...]` placeholders. DOI metadata was checked against Crossref records;
the NDVI record was checked in NASA NTRS, and Sentinel-2 resolution was checked
against the Copernicus/ESA mission reference. This metadata check is not a
substitute for reading the source passages before submission.

| Key | Claim supported in the manuscript | Record check | Remaining action |
|---|---|---|---|
| `chen2020stanet` | STANet and LEVIR-CD context | DOI metadata | Confirm exact dataset description in the source |
| `drusch2012sentinel` | Sentinel-2 mission context | DOI metadata | Confirm the sentence and IEEE style |
| `daudt2018siamese` | Fully convolutional Siamese change detection | DOI metadata | Confirm cited wording against the paper |
| `chen2022bit` | Transformer-based change detection | DOI metadata | Confirm cited wording against the paper |
| `rouse1974vegetation` | NDVI vegetation-index context | NASA NTRS record `19740022614`; page range intentionally omitted because it was not verified | Confirm the original paper supports the precise definition used |
| `zha2003ndbi` | NDBI and built-up mapping | DOI metadata | Confirm the index description against the paper |
| `otsu1979threshold` | Histogram-based threshold selection | DOI metadata | Confirm cited wording and IEEE style |
| `daudt2018oscd` | OSCD dataset and urban-change context | DOI metadata | Confirm split and label details against the source |
| `sentinel2mission` | Sentinel-2 band spatial resolutions | Official Copernicus/ESA mission page | Recheck page and access date before final submission |

## Submission checks

- [ ] Read the cited source passages and make sure each sentence is no stronger
  than its source.
- [ ] Confirm each DOI resolves and that final author/title/venue fields match
  the publisher record.
- [ ] Confirm the NASA NTRS entry's preferred proceedings citation; do not add
  an unverified page range.
- [ ] Apply the target IEEE conference's citation and reference-style rules.
- [ ] Keep dataset licensing and redistribution checks separate; citations do
  not establish permission to use or redistribute data.
- [x] Confirm no citation placeholder remains and every citation key has a
  bibliography entry.

Do not add references merely to make the related-work section look broader.
The paper intentionally avoids unsupported priority, superiority and
test-set-overuse claims.
