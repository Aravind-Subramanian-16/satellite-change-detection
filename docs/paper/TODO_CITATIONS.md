# Citation work list

The manuscript contains deliberate `[CITE: ...]` slots. **No reference, DOI,
author list, year, venue or impact factor has been invented.** Do not submit
the paper until every slot is replaced with a verified source and the sentence
around it has been checked against that source.

For each row: search the named databases, open the publisher/author page,
record the exact bibliographic fields, and add the entry to the BibTeX file
used by the paper. Prefer the dataset's own paper and licence page for dataset
and licence claims.

| Slot | Topic | Why it is needed | Suggested databases | Status |
|---|---|---|---|---|
| 1 | OSCD dataset and benchmark protocol | States the 14/10 city split, label definition and official evaluation context | Dataset site, publisher page, Semantic Scholar, Google Scholar | Unverified |
| 2 | LEVIR-CD dataset | Describes the aerial 0.5 m training data for the provided CNN checkpoint | Dataset site, publisher page, Semantic Scholar | Unverified |
| 3 | Sentinel-2 mission and L2A products | Supports sensor resolution and product description | ESA/CDSE documentation, peer-reviewed mission papers | Unverified |
| 4 | NDVI definition and limitations | Supports the index equation and mixed-pixel caveat | Original index paper, remote-sensing textbooks, Google Scholar | Unverified |
| 5 | NDBI / built-up index definition | Supports the NDBI equation and its reported confusions | Original index paper or a peer-reviewed evaluation | Unverified |
| 6 | Otsu thresholding | Supports the threshold method and its class-balance sensitivity | Original paper, Google Scholar | Unverified |
| 7 | Pseudo-invariant features / relative radiometric normalisation | Needed only if the optional PIF description is retained | Remote-sensing journals, Google Scholar | Unverified |
| 8 | Deep-learning change detection surveys | Provides related-work context without priority claims | Google Scholar, Semantic Scholar, IEEE Xplore | Unverified |
| 9 | Calibration / expected calibration error | Needed only if the optional reliability analysis is reported | ML calibration papers, Google Scholar | Unverified |
| 10 | Reproducibility and benchmark reporting guidance | Supports the reporting checklist and disclosure choices | ACM/IEEE/NeurIPS guidance, Google Scholar | Unverified |
| 11 | OSCD licence (CC BY-NC-SA as recorded in project notes) | Required before redistribution or commercial use | Dataset page and licence text, legal review | Unverified; legal review required |
| 12 | Copernicus data terms and attribution | Required for imagery redistribution | Copernicus Data Space terms, legal review | Unverified; legal review required |
| 13 | OpenStreetMap ODbL | Required for road-context redistribution | OSM Foundation licence page, legal review | Unverified; legal review required |
| 14 | Cross-sensor / domain-shift change detection | Supports the related-work statement that transfer across sensors and resolutions is a known problem | Google Scholar, Semantic Scholar, IEEE Xplore | Unverified |
| 15 | Test-set reuse and benchmark overfitting | Supports the related-work statement that repeated test use can inflate apparent progress | ML methodology papers, Google Scholar | Unverified |
| 16 | Preregistration and one-shot evaluation | Supports the protocol's provenance and the related-work context | COS/registered-reports guidance, ML methodology papers | Unverified |
| 17 | Spatial cross-validation / leave-one-city-out | Supports the validation design; not a claim of novelty | Remote-sensing and spatial-statistics papers, Google Scholar | Unverified |
| 18 | Open change-detection tools and decision-support interfaces | Supports the related-work statement that interactive Earth-observation tools exist | Tool papers, software venues, Google Scholar | Unverified |

## Verification rules

- Quote the source's own wording for dataset splits, licences and metric
  definitions; do not paraphrase a claim into a stronger one.
- Do not add a citation merely to decorate a sentence. Each citation must
  support the specific statement next to it.
- Do not report impact factors, acceptance rates or "first" claims unless the
  owner has separately verified them. Those fields are intentionally absent.
- If a slot cannot be verified, remove the sentence or mark the claim as
  unsupported; do not fill the slot with a guessed reference.
- Re-run the claims audit after the bibliography is inserted, because a
  citation can change the strength of a claim.
