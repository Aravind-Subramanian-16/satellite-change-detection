# Venue options

**All venue details below must be verified on the official call for papers or
author guidelines before submission.** Deadlines, page limits, formatting,
review models, open-access requirements, fees and indexing change. This file
deliberately contains **no impact factors and no acceptance rates**, because
none were verified and quoting them would create an unsupported claim.

The manuscript is currently a negative/engineering result with a small
benchmark and no new method. That constrains the realistic venues: a
tool/software venue or a workshop is a better fit than a methods journal that
expects a competitive score or a new algorithm.

## 1. What the paper currently is

- A reproducible evaluation of five configurations on 10 OSCD test cities.
- A negative transfer result for one mismatched CNN checkpoint.
- A description of provenance, validation-status gating and analysis profiles.
- A preregistered protocol with **no v3 result**.
- No new method, no new dataset, no competitive score, no field validation.

## 2. Venue categories

### A. Software / tool papers

| Venue | Why it might fit | What reviewers will likely expect | Unverified items |
|---|---|---|---|
| **Journal of Open Source Software (JOSS)** | Open, tested implementation with a clear interface; the repository has a test suite and docs. | A functioning open-source package, install/test instructions, clear statement of need, substantial tests, an author-created review issue, and a short paper focused on the software (not the benchmark). | Current scope criteria, paper length, review process, fees. Verify the JOSS author guidelines. |
| **SoftwareX (Elsevier)** | Tool/metadata paper for a working system. | Code metadata, architecture, validation of the software (not necessarily new science), long-term availability, licence. | Article type, length, APC/fees, data/code policy. Verify.
| **Environmental Modelling & Software (Elsevier)** | Decision-support framing and reproducibility may fit. | A stronger evaluation of usefulness, user workflow and software design; likely more than one benchmark. | Scope fit, fees, review timeline. Verify.
| **Computers & Geosciences (Elsevier)** | Implementation + reproducibility. | Novelty or clear methodological contribution beyond a straightforward application; code availability. | Scope fit, fees, article type. Verify.

**Fit assessment:** JOSS or SoftwareX is the most honest home for the
implementation **if** the owner is willing to maintain the repository and the
paper is reframed around the software. The current manuscript is a benchmark
paper, so it would need a separate short software paper, not a trim of the
current text.

### B. Remote-sensing conferences and letters

| Venue | Why it might fit | What reviewers will likely expect | Unverified items |
|---|---|---|---|
| **IEEE IGARSS** | Applied remote-sensing audience; benchmark and tool work can fit. | A 4-page (typically) paper with a clear contribution; competitive results or a strong application story. A negative result may be a hard sell unless framed as an evaluation/benchmark paper. | Page limit, deadline, presentation format, registration/fees. Verify the current call. |
| **IEEE Geoscience and Remote Sensing Letters (GRSL)** | Short, fast remote-sensing paper. | A concise methodological or application contribution; likely expects stronger baselines or a new technique. | Length, fees, scope. Verify.
| **Remote Sensing Letters (Taylor & Francis)** | Short paper option. | Similar concerns: novelty and baselines. | Length, fees, scope. Verify.
| **ISPRS Annals / Archives** | Conference proceedings, reproducibility-friendly. | Full paper with rigorous evaluation; may accept benchmark/negative results if framed well. | Event cycle, review model, fees. Verify.

**Fit assessment:** IGARSS is plausible **only** as an evaluation/benchmark
paper, and it will likely be judged against much stronger OSCD scores. GRSL
and Remote Sensing Letters are poor fits for a negative result without a new
method.

### C. Journals (remote sensing / geoscience)

| Venue | Why it might fit | What reviewers will likely expect | Unverified items |
|---|---|---|---|
| **IEEE JSTARS** | Broad applied remote-sensing journal. | A substantial contribution: new method, extensive comparison, or a systematic benchmark across datasets. One checkpoint and one dataset are likely insufficient. | APC/fees, length, scope. Verify.
| **Remote Sensing (MDPI)** | Fast, open-access; applied papers and negative results appear. | Clear novelty statement, adequate baselines, reproducibility, APC. Reviewers may still demand a stronger method. | APC (potentially high), special-issue fit, review process. Verify current APC and policies.
| **Remote Sensing Applications: Society and Environment (Elsevier)** | Application/decision-support framing. | Demonstrated societal/operational relevance and validation; one urban benchmark may not suffice. | APC/fees, scope. Verify.
| **International Journal of Applied Earth Observation and Geoinformation (Elsevier)** | Applied Earth observation. | Strong applied contribution and validation; likely more than a negative benchmark. | APC/fees, scope. Verify.
| **GIScience & Remote Sensing (Taylor & Francis)** | GIScience/reproducibility angle. | Methodological or theoretical contribution. | APC/fees, scope. Verify.

**Fit assessment:** none of these is a good first target in the current state.
They would require either v3 with a real improvement, a second independent test
set, or non-urban labelled validation. Submitting now risks a desk rejection
and burns the paper's novelty window.

### D. ML workshops and benchmark/negative-result tracks

| Venue | Why it might fit | What reviewers will likely expect | Unverified items |
|---|---|---|---|
| **ML4RS / GeoAI workshops at major ML conferences** | Negative results, reproducibility and remote-sensing evaluation are welcome topics. | Short paper, clear evaluation question, honest limitations; non-archival or workshop proceedings. | Current cycle, archival status, deadlines, travel/registration. Verify.
| **ICLR/NeurIPS workshop on datasets, benchmarks or reproducibility** | The benchmark + disclosure story fits the genre. | A benchmark contribution with sufficient scope, or a reproducibility study. Ten cities and five configurations may be too small for a main benchmark track. | Tracks, page limits, archival status. Verify.
| **ACM SIGSPATIAL workshops (GeoAI, etc.)** | Spatial evaluation/negative results. | Short paper with clear spatial evaluation. | Current workshops, deadlines. Verify.

**Fit assessment:** the best low-risk peer-review target for the current
negative result. A workshop can host an honest evaluation that a journal would
reject for insufficient novelty. It will not confer the prestige of a journal,
and workshop proceedings may be non-archival.

### E. Preprints and community venues

| Venue | Why it might fit | What to check |
|---|---|---|
| **arXiv (cs.CV / eess.IV / cs.SE)** | Fast public disclosure; supports code links. | Endorsement requirements, licence choice, no peer review, permanence. Never post before checking co-author/employer policies and dataset licence.
| **EarthArXiv** | Earth-science preprint server. | Scope, moderation, licence, DOI. Verify.
| **FOSS4G / community talks** | Demo and implementation talk. | Not a peer-reviewed paper; talk proposal deadlines. Verify.

**Fit assessment:** a preprint is useful to timestamp the protocol and
disclose the result, but it does **not** make the work peer-reviewed or
novel. The manuscript is already public in the repository; a preprint adds a
DOI and a citable record. Do not describe it as validation.

## 3. Decision guide

1. **If the goal is a citable software artefact:** JOSS or SoftwareX, with a
   software-focused paper and the benchmark as validation.
2. **If the goal is to publish the negative result quickly:** a remote-sensing
   or ML workshop (ML4RS/GeoAI/reproducibility), clearly labelled as a
   workshop paper.
3. **If the goal is a journal:** do not submit until at least one of the
   following exists:
   - a v3 improvement (or a documented null result) from the preregistered
     protocol;
   - an independent second test set or city-level confidence intervals;
   - labelled validation for at least one non-urban profile;
   - a stronger baseline comparison from published OSCD methods under the same
     protocol.
4. **If the goal is priority:** this checklist cannot support it. Complete the
   external novelty search first (`NOVELTY_CHECKLIST.md`).

## 4. What every venue will require before submission

- Replace all `[CITE: topic]` placeholders with real, verified references.
- Compile and proofread the PDF; check page limits and figure legibility.
- Decide on anonymisation and remove author-identifying repository links if
  required.
- State data/code availability and licence terms; do not redistribute OSCD.
- Disclose AI assistance according to the venue policy.
- Disclose the two prior test-scoring events and the uncomputed v3.
- Confirm that no accuracy number is shown for an unvalidated profile.
- Remove any "first"/"novel"/"state of the art" wording unless externally
  verified.
- Check dual-use/ethics statements and the absence of operational claims.

## 5. Owner decisions required

- Choose between a software paper and a benchmark/negative-result paper; the
  current manuscript cannot be both without becoming two papers.
- Approve any APC or registration fee **after** checking the current amount;
  none is listed here.
- Decide whether a preprint is acceptable to co-authors, employer or funder.
- Decide whether to invest in the v3 run and non-urban labels before a journal
  submission.
- Confirm the licence review before any submission that links to OSCD data.

**No venue has been contacted, no submission has been made, and no deadline has
been verified.**
