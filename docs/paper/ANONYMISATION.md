# Anonymisation checklist

**Current state: NOT anonymised.** The manuscript and repository identify the
author. Nothing in this file has been applied; it records what must be checked
if the chosen venue uses double-blind review.

## 1. Visible identity in the manuscript

`docs/paper/paper.tex` contains:

- an author block naming **Aravind**;
- the **Department of Computer Science and Engineering, Presidency University,
  Bengaluru, India**.

There is no email address in the current author block. The affiliation and name
are sufficient to identify the author.

`docs/paper/paper_draft_revised.docx` contains the same name and affiliation in
the document body.

## 2. File metadata

- The revised DOCX has core properties with `dc:creator` = `IEEE`,
  `cp:lastModifiedBy` = `Diana Romeo`, and a template title
  (“Paper Title (use style: paper title)”). These are template/metadata values,
  not a verified author identity, but they should be removed before sharing an
  anonymised copy.
- A compiled PDF can carry author/title metadata from the LaTeX source and
  hyperref. Check the PDF properties, not only the visible page.
- Images can carry EXIF or software metadata. Check the figures and screenshots
  before releasing them.

## 3. Repository and history

- Git commits record author name, email and timestamps. The local branch is
  ahead of the remote and has not been pushed successfully, but the history is
  still identifying if the repository is shared as-is.
- The git remote URL and repository owner can identify the author.
- Documentation contains absolute home-directory paths (for example
  `/Users/<name>/...`) in evidence JSON and progress notes.
- Screenshots may show local file paths, browser profiles or account names.
- No funding or acknowledgements section exists in the manuscript.
- Do not rewrite git history, force-push or delete the remote as part of
  anonymisation without an explicit owner decision and a backup. A history
  rewrite is a separate, destructive operation.

## 4. What to change for a double-blind submission

1. Replace the author block with an anonymous one, for example
   `Anonymous submission` and no affiliation. Keep a de-anonymised version for
   the camera-ready.
2. Remove acknowledgements, funding statements and any “our previous work”
   phrasing that identifies the group.
3. Strip PDF metadata after compiling; verify with a PDF inspector.
4. Remove DOCX core properties before sharing a DOCX; do not rely on deleting
   visible text only.
5. Scrub EXIF/metadata from figures and screenshots.
6. Replace absolute local paths in any released evidence or logs with relative
   paths.
7. Use an anonymised artifact link (for example, an anonymous repository
   snapshot) rather than the identifying remote. Check that the snapshot does
   not include `.git` history, author names, email addresses or local paths.
8. Check that cited prior work by the same author is cited in the third person
   and does not reveal identity through wording such as “our earlier system.”
   The current manuscript has no such self-citation.
9. Confirm the venue's policy on preprints and artifact links; do not assume
   that an anonymised PDF is sufficient if the repository remains public.
10. Re-run the claims audit and static checks after anonymising; removing an
    author block must not change any claim.

## 5. Verification before submission

- [ ] Manuscript has no author name, affiliation, email or acknowledgements.
- [ ] PDF metadata contains no author identity.
- [ ] DOCX metadata is stripped (if a DOCX is shared).
- [ ] Figures/screenshots have no identifying metadata or visible paths.
- [ ] Repository snapshot has no `.git` history, remotes, author names or
      absolute home-directory paths.
- [ ] Artifact link is anonymous and does not redirect to an identifying page.
- [ ] No self-identifying wording in the text.
- [ ] The de-anonymised camera-ready is stored separately.
- [ ] The owner has explicitly approved any history rewrite; none is performed
      by this checklist.

## 6. Internal documents

This file and `CLAIMS_AUDIT.md` name the author or institution while recording
what must be anonymised. Do not include them in an anonymised artifact
snapshot; keep them in the internal repository and share only the anonymised
manuscript, code and data statement.

## 7. What is not decided here

- Whether the target venue is double-blind.
- Whether the repository will be released with the submission or after
  acceptance.
- Whether a code licence will be added (none is chosen; see `ARTIFACT.md`).
- Whether the author wants a public preprint.

These are owner decisions. Until they are made, the safe description is
“currently identifying; anonymisation not applied.”
