# References to verify

The manuscript contains deliberate `[CITE: ...]` slots. **No reference, author
list, year, venue, DOI, volume, page or impact factor is asserted in this
file.** Every entry below is unverified. The paper must not be submitted until
each slot is replaced by a checked source and the surrounding sentence is
checked against that source.

## Current slots

There are 12 unique topics and 14 body occurrences (Otsu and OSCD each appear
twice), plus the explanatory `[CITE: topic]` example in the References note.

| # | Topic in `paper.tex` | Where used | What the source must support | Status |
|---|---|---|---|---|
| 1 | LEVIR-CD dataset | Introduction | The dataset exists, is aerial, is approximately 0.5 m, and provides bitemporal pairs with pixel labels | Unverified |
| 2 | Deep learning change detection surveys | Introduction | General statement that deep networks report high scores on native-resolution benchmarks | Unverified |
| 3 | Sentinel-2 mission and L2A products | Introduction | 10 m and 20 m bands and the L2A product description | Unverified |
| 4 | Fully convolutional Siamese networks | Related work | The architecture family for bitemporal change detection | Unverified |
| 5 | STANet | Related work | Spatial-temporal attention for change detection | Unverified |
| 6 | BIT | Related work | Transformer-based bitemporal change detection | Unverified |
| 7 | Cross-sensor / domain-shift change detection | Related work | Transfer across sensors, geography or resolution is an acknowledged problem | Unverified |
| 8 | NDVI definition | Related work | The index definition and the mixed-pixel caveat | Unverified |
| 9 | NDBI / built-up index definition | Related work | The index definition and its reported confusions | Unverified |
| 10 | Otsu thresholding | Related work; OSCD protocol (twice) | The histogram threshold method and its class-balance sensitivity | Unverified |
| 11 | OSCD dataset and protocol | Related work; OSCD data (twice) | The 14/10 city split, label definition and official evaluation context | Unverified |
| 12 | Test-set reuse and benchmark overfitting | Related work | Repeated use of a fixed test split can inflate apparent progress | Unverified |

Legacy topics in `TODO_CITATIONS.md` that are **not** used by the current
manuscript (PIF/radiometric normalisation, calibration/ECE, spatial
cross-validation, preregistration, open tools) should not be inserted unless a
sentence actually needs them.

## Known legacy problems

These are recorded so they are not silently “fixed” from memory:

- The original DOCX reference list contains **duplicate STANet entries**
  (its items [1] and [4]). Determine which record is correct only by opening
  the original publication and the publisher page. Do not merge, delete or
  renumber them by recollection.
- The **FC-Siam** citation details must be checked against the original
  publication. The README lists a candidate entry, but a repository README is
  not a bibliographic authority.
- The README also lists a candidate BIT entry with a DOI. Treat it as a lead to
  check at the DOI resolver and publisher page, not as a verified reference.
- No author, year, venue, volume, page, DOI or impact factor is copied into this
  file. That is intentional.

## How to verify one slot

1. Search the named databases for the topic, not for a remembered title. Open
   the publisher page, the authors' page, or the dataset's official page.
2. Record the exact authors, title, venue, year, volume, issue, pages and
   DOI/URL. For datasets, record the version and licence.
3. Read the abstract or the specific section that supports the sentence. If the
   source says something weaker or different, weaken or remove the sentence.
4. Add the BibTeX entry to the paper's bibliography and replace the
   `[CITE: ...]` slot with the citation key.
5. Re-run a static check that no `[CITE: ...]` slots remain and that every
   `\cite{...}` key exists in the bibliography.
6. Re-read the claims audit: a citation can change the strength of a claim.

Suggested databases: the dataset's official site and paper, publisher pages,
Semantic Scholar, Google Scholar, IEEE Xplore, and the DOI resolver. For
licences, use the licence text itself and obtain legal review where required.

## Submission gate

- [ ] All 12 topics resolved to verified records.
- [ ] No `[CITE: ...]` slots remain in `paper.tex`.
- [ ] The bibliography compiles with no undefined keys.
- [ ] Every cited sentence has been checked against its source.
- [ ] Duplicate STANet entries and the FC-Siam record are resolved from
      original sources, not memory.
- [ ] No impact factor, acceptance rate or priority wording has been added.
