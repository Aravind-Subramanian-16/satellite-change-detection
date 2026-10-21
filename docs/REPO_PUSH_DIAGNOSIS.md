# Repository size and push diagnosis

Date: 2026-10-21
Scope: Step 0 of the submission task. Read-only inspection; no history was rewritten.

## Findings

### Working tree and tracked files

- `find . -type f -size +20M` (excluding `venv/` and `.git/`): **no files**.
- `git ls-files` filtered to files larger than 20,000,000 bytes: **no files**.
- Largest tracked blobs are images and a CSV, all under 2 MB (see below).

### Git history

Command:

```bash
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $3 > 20000000 {print $3, $2, $4}' \
  | sort -rn
```

Result: **no output — no blob larger than 20 MB exists in any reachable commit.**

Largest blobs in history:

| Bytes | Path |
| ---: | --- |
| 1,736,594 | `visual_degradation_proof_v2.png` |
| 1,374,938 | `visual_degradation_proof.png` |
| 1,149,275 | `dataset_samples_local.png` |
| 720,267 | `degradation_results.csv` |
| 696,360 | `docs/screenshots/phase_a_dashboard.png` |
| 511,791 | `docs/screenshots/phase_a_landing.png` |
| 422,227 | `docs/screenshots/phase_b_results.png` |
| 401,975 | `docs/screenshots/phase_b_live.png` |
| 184,740 | `decay_curve.png` |
| 172,162 | `test_after.png` |

Repository object store:

```text
count: 241
size: 3.81 MiB
in-pack: 161
packs: 1
size-pack: 4.75 MiB
garbage: 0
```

`.git` on disk: 8.7 MB.

## Conclusion

There is **no evidence** that the HTTP 400 push failure is caused by a file over
20 MB, a GitHub 100 MB limit, or an oversized pack. The five prior failures
(`RPC failed; HTTP 400 curl 22`, `send-pack: unexpected disconnect while reading
sideband packet`) are consistent with a transport/proxy/remote problem, not a
large-blob rejection. History rewriting is therefore **not indicated** and was
not performed.

Follow-up: after committing this report and the `.gitignore` additions
(commit `8989525`, no file over 2 MB), `git push origin main` failed with the
same error:

```text
error: RPC failed; HTTP 400 curl 22 The requested URL returned error: 400
send-pack: unexpected disconnect while reading sideband packet
fatal: the remote end hung up unexpectedly
```

This is a second data point against a large-file cause: a small commit also
fails. The local branch remains ahead of the remote; no force push was used.

Before rewriting anything, capture the failing request:

```bash
GIT_TRACE=1 GIT_CURL_VERBOSE=1 git push --verbose origin main
```

Check whether the failure reproduces on a minimal branch, for example:

```bash
git branch push-probe main
git push origin push-probe
```

If the probe also fails, the problem is connection-side, not history-side.

## Exact history-rewrite commands (NOT RUN)

These are provided only in case a future large blob is actually found. Rewriting
history changes every commit hash and requires a force push; coordinate with any
other clone first. Make a mirror backup before running either tool.

Backup:

```bash
git clone --mirror \
  https://github.com/Aravind-Subramanian-16/satellite-change-detection.git \
  satellite-change-detection-backup.git
```

### git-filter-repo

Install (in the project venv):

```bash
python -m pip install git-filter-repo
```

Strip every blob larger than 20 MB:

```bash
git filter-repo --strip-blobs-bigger-than 20M --force
```

Or remove one path from all history:

```bash
git filter-repo --path path/to/large-file --invert-paths --force
```

Then restore the remote and force-push:

```bash
git remote add origin \
  https://github.com/Aravind-Subramanian-16/satellite-change-detection.git
git push --force-with-lease origin main
```

### BFG Repo-Cleaner

```bash
java -jar bfg.jar --strip-blobs-bigger-than 20M \
  satellite-change-detection.git
cd satellite-change-detection.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

## Preventive `.gitignore` additions

Added in this step:

```gitignore
# ── Archives & media (keep out of history) ──────────────
*.zip
*.7z
*.tar
*.tar.gz
*.tgz
*.mp4
*.mov
*.avi
*.mkv

# ── LaTeX build artefacts ────────────────────────────────
docs/paper/*.aux
docs/paper/*.log
docs/paper/*.out
docs/paper/*.toc
docs/paper/*.bbl
docs/paper/*.blg
docs/paper/*.fls
docs/paper/*.fdb_latexmk
docs/paper/*.synctex.gz
docs/paper/*.pdf

# ── Large result artefacts ───────────────────────────────
results/
*.csv.gz
*.h5
*.hdf5
*.pkl

# ── Colab / notebook checkpoints ─────────────────────────
.ipynb_checkpoints/
```

Note: `*.pt`, `*.onnx`, `*.pth`, `*.joblib`, `dataset/`, `venv/` and
`analysis_history.sqlite3` were already ignored before this step.

## Evidence retention

Figures and screenshots should stay below roughly 2 MB each. If a future
screenshot exceeds that, downscale it or export PNG at a smaller viewport rather
than committing it unchanged.
