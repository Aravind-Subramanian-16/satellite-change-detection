# Novelty checklist

**Status: unverified.** This document records a shallow literature scan, not a
systematic review. It does **not** establish priority, novelty or superiority,
and nothing in the manuscript may be changed to "first", "novel" or
"state of the art" on the strength of it.

- Scan date: 2026-10-21.
- Tool/index: Qoder `WebSearch` (a general web index returning titles, snippets
  and URLs). Publisher pages, arXiv, GitHub, IEEE DataPort and institutional
  guides appeared in results.
- Not searched: Web of Science, Scopus, Google Scholar, Semantic Scholar API,
  the full IEEE Xplore or ACM Digital Library, or any systematic-review
  database. No query strings were pre-registered, no deduplication or screening
  protocol was used, no PRISMA-style flow was recorded, and paywalled full texts
  were not read.
- Metadata below (authors, years, venues, snippets) is reproduced as returned
  by the search index and has **not** been verified against the publisher
  record. Several snippets are truncated or omit the venue.
- A "lead" below means "worth reading", not "supports or refutes novelty".

## Contributions as currently worded

The paper claims three contributions, all of which are *engineering and
reporting* contributions rather than algorithmic ones:

1. **C1 — Auditable implementation.** An end-to-end, browser-based
   Sentinel-2 change-detection tool that records scenes, dates, thresholds,
   cloud masking and commit provenance, and that suppresses accuracy claims for
   profiles that have not been validated.
2. **C2 — Train-only benchmark with negative transfer.** A reproducible OSCD
   test-split evaluation of spectral rules and a CNN baseline trained on
   different-sensor imagery, with a disclosed history of prior test scoring and
   no post-hoc tuning.
3. **C3 — Preregistered validation-only protocol.** A fixed, leave-one-city-out
   improvement search over the 14 OSCD training cities, with a one-shot test
   protocol that is left uncomputed in this repository.

For each contribution, the operational question is only: *do close prior
examples exist that would make a priority claim unsafe?* The answer for all
three is **yes, plausible close work exists or cannot be excluded**, so the
claim remains unverified.

---

## C1 — Auditable Sentinel-2 decision-support implementation

**What would have to be true for novelty:** no published or openly available
system combines Sentinel-2 change analysis with per-result provenance,
validation-status gating and cloud/mask reporting in a deployable interface.

**Searches (5):**

| # | Query | Index / date | Selected leads returned | Reading |
|---|-------|--------------|-------------------------|---------|
| 1 | satellite change detection web application provenance decision support | Qoder WebSearch, 2026-10-21 | EarthDaily "AI-Powered Change Detection for Defense" `https://earthdaily.com/defense-change-detection`; "Deep Learning–Geographic Information System Framework…" (Sensors/myu-group PDF) `https://sensors.myu-group.co.jp/sm_pdf/SM4373.pdf`; Farooq et al., "Satellite-based change detection in multi-objective scenarios" (ScienceDirect, 2024) `https://www.sciencedirect.com/science/article/abs/pii/S2352938524000326`; FlyPix "27 Best Change Detection Tools (2026)" `https://flypix.ai/change-detection-tools/` | Commercial tools advertise decision support; none of the snippets documents per-result thresholds/provenance. Absence in snippets is not absence in the products. |
| 2 | Sentinel-2 change detection open source dashboard validation status | Qoder WebSearch, 2026-10-21 | Copernicus Data Space Sentinel-2 collection `https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2`; Gascon et al., Sentinel-2A calibration/validation (MDPI Remote Sensing, 2017) `https://www.mdpi.com/2072-4292/9/6/584`; offnadir-delta guide (2026) claims an interactive map with change detection `https://offnadir-delta.com/blog/sentinel-2-complete-guide`; ESA eo4society project `https://eo4society.esa.int/projects/land-cover-change-detection-and-monitoring-methodologies-based-on-the-combined-use-of-sentinel-1-and-sentinel-2-for-natural-resources-and-hazard-management/` | At least one commercial guide advertises interactive change detection. "Validation status" did not surface our specific gating pattern; weak negative evidence only. |
| 3 | reproducible research provenance metadata remote sensing workflow | Qoder WebSearch, 2026-10-21 | Kedron et al., "How to Improve the Reproducibility, Replicability, and…" (MDPI Remote Sensing, 2022) `https://www.mdpi.com/2072-4292/14/21/5471`; ISPRS Archives 2025 on reproducibility challenges `https://isprs-archives.copernicus.org/articles/XLVIII-4-W13-2025/87/2025/isprs-archives-XLVIII-4-W13-2025-87-2025.pdf`; Zenodo "Provenance Tools & Workflows for Reproducible Research" (2026) `https://zenodo.org/records/20624453` | Provenance and reproducibility for remote sensing are active, established topics. Our implementation is an instance, not a new concept. |
| 4 | Sentinel-2 change detection decision support provenance reproducibility | Qoder WebSearch, 2026-10-21 | MDPI Remote Sensing 15(3):628 `https://www.mdpi.com/2072-4292/15/3/628`; ResearchGate ensemble-learning record `https://www.researchgate.net/publication/397002929`; arXiv 2101.08122 `https://arxiv.org/abs/2101.08122`; "awesome-remote-sensing-change-detection" `https://github.com/wenhwu/awesome-remote-sensing-change-detection`; ESA eo4society project (above) | Many change-detection systems and tool lists exist. No direct hit on a provenance-gated public web tool, but the scan is far from exhaustive. |
| 5 | open source satellite change detection web application Sentinel-2 | Qoder WebSearch, 2026-10-21 | Kopec et al. (ScienceDirect, 2025) `https://www.sciencedirect.com/science/article/abs/pii/S2352938525003179`; Sen2Extract (arXiv 2404.04305) `https://arxiv.org/pdf/2404.04305`; awesome list (above); FlyPix list (above); EOS Data Analytics `https://eos.com` | Open tools for Sentinel-2 extraction and commercial change-detection platforms exist. C1 is therefore **unverified** and should be framed as an implementation report, not as a new capability. |

**Verdict: unverified.** The closest risk is the mature reproducibility/
provenance literature plus commercial decision-support tools. The paper avoids
priority language and should continue to do so.

---

## C2 — Train-only OSCD benchmark and reported negative transfer

**What would have to be true for novelty:** no prior OSCD study reports a
CNN trained on non-OSCD aerial imagery under a train-only threshold protocol
with disclosed repeated test scoring, or none reports the resulting failure
without tuning it away.

**Searches (5):**

| # | Query | Index / date | Selected leads returned | Reading |
|---|-------|--------------|-------------------------|---------|
| 1 | OSCD benchmark spectral indices CNN change detection evaluation | Qoder WebSearch, 2026-10-21 | Feng et al., MSAK-Net (MDPI Remote Sensing 14(21):5368, 2022) `https://www.mdpi.com/2072-4292/14/21/5368`; survey arXiv 2305.05813 `https://arxiv.org/html/2305.05813v1`; SciELO spectral-similarity paper (no stable URL captured); Daudt et al. HAL record `https://hal.science/hal-01899024v1/document`; OSCD project page `https://rcdaudt.github.io/oscd/` | OSCD has a substantial CNN literature with much higher reported scores than ours. We make no competitive claim. |
| 2 | Onera Satellite Change Detection dataset baseline results | Qoder WebSearch, 2026-10-21 | IEEE DataPort OSCD record `https://ieee-dataport.org/open-access/oscd-onera-satellite-change-detection`; OSCD project page (above); Daudt et al. arXiv 1810.08468 `https://arxiv.org/abs/1810.08468`; OpenReview record on OOD robustness (URL not captured); DS_UNet GitHub (URL not captured) | Baselines and robustness discussions exist. The scan did not establish whether any reports this exact cross-sensor negative transfer. |
| 3 | negative transfer CNN Sentinel-2 change detection aerial imagery | Qoder WebSearch, 2026-10-21 | Pegia et al., "Learning Change Detection over Sentinel-2 Image Pairs" (ACM, 2022) `https://dl.acm.org/doi/fullHtml/10.1145/3549555.3549574`; Owens thesis (BYU, 2020) `https://brightspotcdn.byui.edu/ee/0c/ec6a93ad41eda1b8503e0133d056/braxton-owensf20.pdf`; Peng et al. review (ScienceDirect, 2025) `https://www.sciencedirect.com/science/article/pii/S1569843224006381`; change-detection list `https://github.com/liy974/change-detection` | Sentinel-2-specific CNN work exists; so do general negative-transfer discussions. We found no direct match for an aerial-trained checkpoint evaluated on OSCD, but search snippets cannot rule it out. |
| 4 | cross-sensor transfer change detection Sentinel-2 CNN benchmark | Qoder WebSearch, 2026-10-21 | Saidi et al., multi-modal change detection review (MDPI Remote Sensing 16(20):3852, 2024) `https://www.mdpi.com/2072-4292/16/20/3852`; awesome list (above); Pegia et al. (above); "A Survey of Sample-Efficient Deep Learning for Change Detection" (arXiv 2502.02835) `https://arxiv.org/html/2502.02835v1`; Yu et al. (IEEE, 2025) `https://ieeexplore.ieee.org/iel8/4609443/10766875/11146768.pdf`; Daudt IGARSS paper `https://rcdaudt.github.io/files/2018igarss-change-detection.pdf` | Cross-sensor transfer is a recognised problem. Our result is a data point, not a new problem statement. |
| 5 | OSCD test set leakage benchmark overfitting change detection | Qoder WebSearch, 2026-10-21 | "On Leakage of Code Generation Evaluation Datasets" (arXiv 2407.07565) `https://arxiv.org/html/2407.07565v1`; Ni et al., "Training on the Benchmark Is Not All You Need" (AAAI, 2025) `https://ojs.aaai.org/index.php/AAAI/article/view/34678/36833`; MSAK-Net (above); Koleiev et al., end-user audit (PMC, 2026) `https://pmc.ncbi.nlm.nih.gov/articles/PMC13417885/` | Test-set leakage/overuse is well studied in ML generally. The scan found no OSCD-specific audit, but that does not establish that ours is the first. |

**Verdict: unverified.** A CNN trained on aerial imagery is a poor match to
OSCD by construction, so the negative result is neither surprising nor
novel in itself. The paper reports it as an auditable failure and does not
claim discovery.

---

## C3 — Preregistered validation-only improvement protocol

**What would have to be true for novelty:** no prior satellite change-detection
study uses a publicly timestamped, leave-one-city-out, validation-only protocol
with a one-shot test-score commitment.

**Searches (5):**

| # | Query | Index / date | Selected leads returned | Reading |
|---|-------|--------------|-------------------------|---------|
| 1 | preregistration remote sensing model evaluation protocol | Qoder WebSearch, 2026-10-21 | Unsupervised multimodal registration paper (levir.buaa.edu.cn PDF, 2023) `https://levir.buaa.edu.cn/static/pdfs/2023_bin_pan_unsupervised.pdf` — snippet says "experimental data were pre-registered"; Zhang et al. registration review (MDPI Remote Sensing, 2021) `https://www.mdpi.com/2072-4292/13/24/5128`; Feng et al. "MID" (MDPI Remote Sensing, 2022) `https://www.mdpi.com/2072-4292/14/17/4178`; Torun et al. review (MDPI Remote Sensing, 2026) `https://www.mdpi.com/2072-4292/18/20/3479` | One remote-sensing paper mentions pre-registration, but not for a change-detection test split. General preregistration in remote sensing is not obviously common. Weak evidence, not proof of a gap. |
| 2 | leave-one-city-out validation satellite change detection | Qoder WebSearch, 2026-10-21 | Höhn et al., landslide dataset (Scientific Data, 2025) `https://www.nature.com/articles/s41597-025-06167-2` — geographically clustered leave-one-out validation with Sentinel-2; Stock et al., iterative spatial leave-one-out CV (Taylor & Francis, 2022) `https://www.tandfonline.com/doi/abs/10.1080/15481603.2022.2107113`; "Jane Jacobs in the Sky" (arXiv 2102.00848) `https://arxiv.org/html/2102.00848v1`; Debus et al. (ScienceDirect, 2025) `https://www.sciencedirect.com/science/article/pii/S235293852500206X` | Spatial leave-one-out validation is established in remote sensing. Our use of it is standard, not novel. |
| 3 | one-shot evaluation held-out test set change detection benchmark | Qoder WebSearch, 2026-10-21 | GOT-10k (IEEE TPAMI, 2021) `https://www.computer.org/csdl/journal/tp/2021/05/08922619/1fvZgA2wezK` — one-shot protocol; Corley et al., "A Change Detection Reality Check" (ICLR 2024 workshop) `https://ml-for-rs.github.io/iclr2024/camera_ready/papers/46.pdf`; Hassouna et al. benchmarking framework preprint (2024) `https://www.preprints.org/manuscript/202403.1106`; changedetection.net (ResearchGate) `https://www.researchgate.net/publication/232905474_changedetectionnet_A_New_Change_Detection_Benchmark_Dataset` | One-shot evaluation is an established benchmark idea outside this specific task. A "reality check" paper already questions change-detection evaluation practice. |
| 4 | preregistration geospatial remote sensing study protocol | Qoder WebSearch, 2026-10-21 | CASRAI "Preregistering a Study Protocol: A Guide" `https://casrai.org/guides/preregistration-of-a-study-protocol`; Center for Open Science preregistration `https://www.cos.io/initiatives/prereg`; Hukkelhoven thesis (WUR) `https://edepot.wur.nl/578660`; HKU library guide `https://libguides.lib.hku.hk/openscience/preregistration`; UQ library guide `https://web.library.uq.edu.au/research-and-publish/open-research/preregister-your-research` | Preregistration infrastructure and guidance are mature. We found no exemplar applying it to an OSCD test score, but that is not evidence that none exists. |
| 5 | test set reuse overfitting remote sensing benchmark evaluation | Qoder WebSearch, 2026-10-21 | "Test set reuse" (mlbenchmarks.org) `https://mlbenchmarks.org/pdf/05-test-set-reuse.pdf`; Feldman et al. (ICML, 2019) `https://arxiv.org/abs/1905.10360`; Mania et al., "Model Similarity Mitigates Test Set Overuse" (NeurIPS) `http://papers.neurips.cc/paper/9190-model-similarity-mitigates-test-set-overuse.pdf`; Gossmann et al. (SPIE, 2018) `https://ui.adsabs.harvard.edu/abs/2018SPIE10577E..0KG/abstract`; Liu et al. cross-domain scene classification (MDPI Remote Sensing, 2022) `https://www.mdpi.com/2072-4292/14/18/4635` | The problem of test-set reuse is well known. Our disclosure of two prior scoring events is good practice, not a methodological invention. |

**Verdict: unverified.** The protocol is a disciplined application of existing
ideas (spatial CV, preregistration, one-shot holdout). It must not be presented
as a new validation method.

---

## What this scan does not support

- It does **not** support any wording such as "first", "novel", "unlike prior
  work", "state of the art", "outperforms" or "fills a gap".
- It does **not** establish that the three contributions are absent from the
  literature. It only records that the searches above did not surface an exact
  match within their snippets.
- It does **not** verify the metadata, claims or quality of any lead. Several
  search snippets contain marketing copy or truncated venue information.
- It does **not** cover non-English literature, theses, patents, project
  reports, internal tools or paywalled full texts.

## Required before any novelty claim

1. A librarian-assisted or systematic search in at least Web of Science,
   Scopus, IEEE Xplore and Google Scholar, with recorded query strings and
   screening.
2. Full-text reading of the closest leads for each contribution (at minimum
   Pegia et al. 2022; the OSCD papers and project page; the MSAK-Net paper;
   the reproducibility paper by Kedron et al.; the spatial CV paper by Stock
   et al.; and "A Change Detection Reality Check").
3. A written statement from the owner that a priority claim is intended and
   has been checked externally.
4. If any claim survives, add exact citations to `TODO_CITATIONS.md` and rerun
   `CLAIMS_AUDIT.md`; otherwise keep the engineering-report framing.

**Overall status: unverified. No novelty claim is permitted.**
