# Submission notes and hand-off

Date: 2026-10-21. **Status: NOT READY TO SUBMIT.** The repository contains a
complete draft, evidence audits, a talk and a verified local UI, but the
blocking items in `SUBMISSION_CHECKLIST.md` are still open. No claim below is a
new experimental result.

## 1. Final local verification

Command:

```bash
./venv/bin/python -m pytest -q
```

Final output:

```text
137 passed, 3 skipped, 1 warning in 19.61s
```

The three skips are environmental, not failures:

| Skip | Reason |
|---|---|
| `tests/test_oscd_label.py:13` | `rasterio` is benchmark-only and not installed locally |
| `tests/test_finetune_cnn.py:44` | `torch` is not installed locally |
| `tests/test_regression_and_api.py:15` | dataset sample `dataset/test/A/test_100_0_0.png` is absent |

No OSCD test city was scored, no model was trained or fine-tuned, no v3 run was
made, and `best_model.pt` / `model.onnx` were not modified.

## 2. What is present

| Deliverable | Path | Evidence |
|---|---|---|
| IEEEtran manuscript | `docs/paper/paper.tex` | 15 `[CITE: ...]` occurrences: 14 body slots plus one explanatory example; no bibliography; not compiled |
| Generated paper assets | `docs/paper/figures/` | Two figures, two tables and `figure_manifest.json`, generated from saved JSON/CSV |
| Claims and validity audits | `docs/paper/CLAIMS_AUDIT.md`, `THREATS_TO_VALIDITY.md`, `REVIEWER_OBJECTIONS.md` | 39 claim rows, 12 objections, explicit not-claimed list |
| Artifact and reproducibility | `docs/paper/ARTIFACT.md` | Commands, hashes, seeds, missing assets and owner actions |
| Training-only LOCO result | `benchmarks/results/oscd_loco_thresholds.json` | 14 training cities; hardcoded F1 0.0976, percentile 0.1469; no test label read |
| Colab model check | `benchmarks/results/colab_model_check.json` | 33,268,410 bytes; SHA-256 `41c2ab64...`; onnxruntime load `true`; inputs `input_a`, `input_b` |
| Talk | `docs/presentation/slides.pptx` | 12 slides, 13.333 x 7.5 in, all 12 with notes |
| Speaker script | `docs/presentation/speaker_notes.md` | 1,253-word script, 9:45 timing table plus 0:15 buffer |
| Slide claim audit | `docs/presentation/CLAIMS_ON_SLIDES.md` | Every slide number mapped to a saved evidence file |
| Reviewer Q&A | `docs/presentation/QA.md` | Exactly 20 numbered questions plus "If you do not know" |
| Demo script | `docs/presentation/DEMO.md` | 2:00 script and a labelled mocked-still fallback; no recording committed |
| Handout | `docs/presentation/handout.pdf` | One A4 page, 595.28 x 841.89 pt; repository URL/DOI line is a TODO |
| Colab hand-off | `notebooks/run_all_colab.ipynb` | Run on Colab 2026-10-21 at `e8b6678`; summary, LOCO and model-check artifacts present |
| Colab summary renderer | `benchmarks/colab_run_summary.py` | Reads only saved artifacts; rejects test-city leakage |
| Local app | `app.py`, `static/` | Verified with synthetic/mocked inputs, not real CNN inference |

Key hashes at hand-off:

```text
37ffe2bbd01a43c07f04740847843f0176ea1118c17283456c34d2ff2a2bef8f  benchmarks/results/oscd_results_v2.json
4c301920d03d09dbc416d82fa76b93e76e1fab9b74bc2db5155da9735965fa88  degradation_results.csv
32d1dbf57d83a1c68c76de0d64856795c082498788428c8206fd7cf2a4a2e29d  benchmarks/results/oscd_loco_thresholds.json
ec452724a09c915a6577b535146bd78fe5f09dd9ce13421d8359057709c3902a  benchmarks/results/colab_model_check.json
77177c595f2a80aa71c3e9d5ff2dc9b31bf7b976a5a909e1a58152507dffeca6  benchmarks/results/COLAB_RUN_SUMMARY.md
d6ab6330ea94c9cc2a6b4b185bddf1ce98e8e7fa52a7051ef6751f08c589a767  docs/paper/paper.tex
353edfd693811491b096b6060441dd6b3ede0fff7eeab9c8344165bbf5b48795  docs/presentation/slides.pptx
ee25e45b427abcb586499c2bac4555b2762ea64c1933b6b85be19d2cb637d2f5  docs/presentation/handout.pdf
67285976fb7b14035f076d9093420e56a259ae68ffd29300b4a38637cf2aa278  notebooks/run_all_colab.ipynb
```

Rebuild the generated material with:

```bash
./venv/bin/python scripts/make_paper_figures.py
./venv/bin/python scripts/make_slides.py
./venv/bin/python scripts/make_handout.py
./venv/bin/python -m pytest -q
```

## 3. Open problems and pending actions

1. **The Step 7b commit is local.** The push blocker was resolved on 2026-10-21
   by switching the git client to HTTP/1.1; remote `main` contains the prior
   commits through `e8b6678`. The Step 7b documentation commit still needs an
   ordinary push. Do not force-push.
2. **No verified citations or bibliography.** The manuscript has 14 body
   placeholders and one explanatory example. Every reference entry is
   unverified, and the legacy README reference list is explicitly marked
   unverified.
3. **The paper has not been compiled.** There is no TeX engine on this host.
   Page count, layout, table widths and figure placement are unverified.
4. **No author metadata.** Author names, affiliations, corresponding author,
   ORCIDs, contributions, funding, conflict-of-interest and AI-assistance
   disclosure are blank or unconfirmed.
5. **No code licence.** None has been chosen. OSCD, Copernicus and OSM terms
   have not received legal review.
6. **The app is not end-to-end validated.** The Drive checkpoint is verified on
   Colab (33,268,410 bytes, load `true`), but it is absent locally; the
   previously present 60,534,573-byte file failed protobuf loading. Real CNN
   inference, live Copernicus fetches and public deployment remain unverified.
7. **Docker and remote CI are unverified.** `docker` is not installed locally.
   The push now succeeds over HTTP/1.1, but the GitHub Actions result has not
   been checked from this checkout.
8. **The Colab hand-off is complete, but the paused notebooks are not.** The run
   at `e8b6678` produced the LOCO JSON, model-check JSON and summary; it did not
   read a test label or score a test city. The learned-classifier and
   auto-improvement notebooks remain unrun with no results.

## 4. Manual steps, in order

1. **Push the Step 7b commit from the owner terminal (no force).**
   The HTTP/1.1 setting fixed the earlier HTTP 400; remote `main` already
   contains the commits through `e8b6678`. Run:
   ```bash
   cd "/Volumes/My Passport/Projects/Mini Project/satellite-change-detection"
   git status -sb
   git log --oneline origin/main..main
   git push origin main
   git ls-remote origin refs/heads/main
   ```
   The local and remote `main` hashes must match. Do not use `--force` and do
   not rewrite history.

2. **Verify the completed Colab artifacts; do not rerun them on the test split.**
   `benchmarks/results/COLAB_RUN_SUMMARY.md` (SHA-256 `77177c59...`) records the
   Colab pytest line `144 passed, 1 skipped, 7 warnings in 15.79s`, the
   training-only LOCO table and the model check. The source JSONs are
   `oscd_loco_thresholds.json` (`32d1dbf5...`) and `colab_model_check.json`
   (`ec452724...`). The run did not unzip test labels or score a test city. If a
   reproduction is ever needed, rerun only the training-only procedure and
   disclose it. The learned-classifier and auto-improvement notebooks remain
   optional and unrun.

3. **Place the verified model locally and verify real inference.**
   The Colab model check confirms the Drive `model.onnx` is 33,268,410 bytes,
   SHA-256 `41c2ab64...`, loads in onnxruntime and has inputs `input_a`,
   `input_b`. Put that file at the repository root; do not use the invalid
   60,534,573-byte file. Start the app, check `GET /model-status`, run a real
   `/predict` pair, and record the result. Until then, the app's real inference
   status is unverified.

4. **Compile and finish the paper on Overleaf.**
   Use IEEEtran conference format and compile twice. Replace all 14 body
   `[CITE: ...]` slots with verified references and add a bibliography. Check
   the four-page limit excluding references, the longtable width, figure
   resolution, captions and line/page numbering. Fill the author block,
   affiliations, corresponding author and ORCIDs; resolve the "Anonymous review
   version --- do not submit as-is" line.

5. **Verify every citation and claim.**
   Work through `docs/paper/REFERENCES_TO_VERIFY.md` and
   `docs/paper/TODO_CITATIONS.md`. Open the original source for every record;
   do not trust the legacy README entries or their DOIs. Add published
   baselines only with comparable protocols and citations, or keep the paper's
   explicit statement that no baseline comparison is made. No priority or
   originality claim is allowed until the external novelty check is complete.

6. **Choose a code licence and obtain legal review.**
   Decide whether to add a `LICENSE`; none exists. Verify OSCD
   (CC BY-NC-SA as recorded), Copernicus Data Space terms, OpenStreetMap ODbL
   and the checkpoint's provenance before redistribution, commercial use or a
   public demo. This is a blocking item for a commercial venue.

7. **Build and test the deployment.**
   After the push works, run:
   ```bash
   docker build -t satellite-change .
   docker run --rm -p 8000:8000 --env-file .env satellite-change
   curl -s http://localhost:8000/health
   ```
   Check the GitHub Actions run. No Docker build, image size, Render deployment
   or CI result has been verified here.

8. **Get an independent review.**
   Ask a reviewer who did not build the project to check `paper.tex` against
   `benchmarks/results/oscd_results_v2.json`, `degradation_results.csv` and the
   code. Record the reviewer's name and comments outside the manuscript if the
   venue requires anonymity.

9. **Decide the scope of paused experiments.**
   The learned classifier, auto-improvement, fusion, uncertainty and
   fine-tuning paths have synthetic tests but no real results. Do not report
   their performance. If v3 is wanted, write and test a protocol-compliant
   scorer **before** any test access, run it once under the frozen protocol,
   never tune after seeing results, and disclose every earlier scoring event.
   Do not run v3 while the paper is under review unless the venue and protocol
   allow it.

10. **Record the demo if required.**
    No demo recording is committed. The 2:00 script and the labelled
    mocked-still fallback are in `docs/presentation/DEMO.md`. A recording must
    not be presented as real inference if it uses mocked responses.

11. **Complete submission metadata.**
    Decide on anonymisation, preprint policy, target venue, author approvals,
    funding/COI statements and the venue's AI-assistance disclosure. Check that
    no credential, personal email, Drive path or sensitive location appears in
    the manuscript, screenshots, logs or supplement.

## 5. Every claim that is still unverified

### Manuscript and references

- Every one of the 14 body citations and the explanatory `[CITE: topic]`
  example: no source has been verified and no bibliography exists.
- All reference metadata, DOIs and legacy README reference entries.
- The four-page limit, total page count, layout, table widths and PDF rendering.
- Author names, affiliations, corresponding author, ORCIDs and contributions.
- Funding, conflict-of-interest and AI-assistance disclosure.
- Any published baseline comparison, ranking or priority/originality claim.
- The independent novelty search; `NOVELTY_CHECKLIST.md` is shallow and marked
  unverified.

### Evaluation and results

- Real CNN inference with the verified 33,268,410-byte `model.onnx`; the file is
  absent locally. The Colab check verifies its size, SHA-256, input names and
  onnxruntime load, not the app's predictions. The invalid 60,534,573-byte file
  is not used.
- The learned-classifier and auto-improvement notebooks: no output exists.
- ONNX input/output names and behaviour; real `/predict` inference.
- Real Copernicus catalog search, scene download, SCL masking and live spectral
  analysis. Phase B screenshots used mock API responses and are labelled as
  such; Phase A's result was synthetic.
- End-to-end report/export generation from a real analysis. The verified PDF,
  CSV and GeoJSON exports came from a saved synthetic result.
- Operational accuracy, deployment safety, user studies and any claim that the
  tool is production-ready. The app has no authentication.
- Causality: the OSCD comparison confounds resolution with sensor, geography
  and season; no causal claim is supported.
- The total number of times the official test split has been scored; the event
  count is unrecorded. v2 is not an independent test.
- v3: no scorer, run or result exists.
- Learned classifier, auto-improvement, fusion, uncertainty, compositing, PIF,
  morphological cleanup and fine-tuning: synthetic tests only, no real
  validation results.
- The training seed is unrecorded; the study has one checkpoint and one
  training run. Do not imply seed variance or architecture variance.
- A formal screen-reader, zoom and accessibility audit was not performed.
- Docker image size/build, Render deployment, GitHub Actions and remote CI.
- The Step 7b documentation commit is not yet on the remote; the prior history
  through `e8b6678` is.

### Documentation and licensing

- The legacy README reference metadata and DOIs; the entries are now marked
  unverified and the unverified STANet/BIT comparison rows were removed.
- Any earlier README claim about Docker image size or a size reduction; the
  numbers were unverified projections and have been removed.
- OSCD, Copernicus and OSM licence terms and legal review.
- The checkpoint's training-data licence and provenance.
- The repository URL, DOI line and handout repository link are TODOs; no DOI
  has been issued.

## 6. Wording and scope rules

- Do not make priority, originality or superiority claims, and do not describe
  the evaluation as a single-attempt or confirmed independent test. Do not call
  the tool a validated product.
- Do not present `docs/paper/PREREGISTRATION.md` as evidence that the
  evaluation is independent or that the result is confirmed.
- Do not claim that all CNNs fail at 10 m, that resolution is the sole cause of
  the OSCD result, or that the spectral rules are a recommended fallback.
- Do not claim that the CNN was fine-tuned, retrained or evaluated on unseen
  cities.
- Do not claim that v3 was run or that a new score exists.
- Do not claim more than the saved Colab summary: the run verifies training-city
  LOCO thresholds and a model load, not test performance, live behaviour or app
  inference. The learned-classifier and auto-improvement notebooks have no
  results.
- Do not publish a repository URL or DOI that has not been checked in a
  logged-out browser or issued by the archive.

## 7. Definition of done for this hand-off

The hand-off is complete for this checkout. The paper is not submission-ready
until the open items in section 3 are closed and the owner has:

- pushed the Step 7b commit and confirmed the remote hashes match;
- kept the completed Colab artifacts in place and not rerun them on the test
  split (the training-only run is already recorded);
- placed the verified model locally and verified real inference;
- compiled the paper, replaced all citations and confirmed the page limit;
- chosen a licence and completed legal review;
- obtained independent review;
- completed author, venue and disclosure metadata.

Until then, report every item in section 5 as unverified.
