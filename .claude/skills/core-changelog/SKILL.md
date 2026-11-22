---
name: core-changelog
description: Add changelog entries for PreTeXt core changes since the last CLI release. Use when preparing a CLI release, or when asked to "add core commits to the changelog" or "update the changelog from core".
---

# Add PreTeXt core changes to the CLI changelog

Before a CLI release, summarize the user-facing changes in PreTeXt core (the `pretext` repo, usually at `../pretext`) that the CLI release will pick up, and add them to the `[Unreleased]` section of `CHANGELOG.md`.

## 1. Find the commit range

- **Start:** the core commit given in the most recent release section of `CHANGELOG.md`, on the line `Includes updates to core through commit: [abc1234](…/commit/<full sha>)`. Use the full SHA from the link.
- **End:** `CORE_COMMIT` in `pretext/__init__.py`.
- In the core repo, run `git fetch -q origin`, then check whether `CORE_COMMIT..origin/master` is empty. If core has newer commits, tell the user that `CORE_COMMIT` is behind, since this release would not include them. Ask whether to bump it; do not bump it yourself.

Do **not** add the `Includes updates to core through commit` line yourself. `scripts/update_changelog.py` writes it at release time from `CORE_COMMIT`.

## 2. Read the commit messages

Read only the commit messages, not the diffs:

```bash
cd ../pretext
git log --no-merges --format='%h %ad %s' --date=short <start>..<end>
git log --merges --format='%h %s' <start>..<end>
```

The merge commits (`Merge: <topic> (PR #NNNN)`) show how the individual commits group into features. Core commit messages begin with the area of the code they touch (`Assembly:`, `LaTeX:`, `EPUB:`, `Publisher variables:`, `Guide:`, …).

## 3. Decide what goes in

**Include** changes that authors or publishers would notice in their output or source:

- new elements, attributes, or publisher variables
- output fixes for any format (HTML, LaTeX/PDF, EPUB, XSL-FO, Beamer, reveal.js, Runestone, …)
- fixes to asset generation (PreFigure, Asymptote, latex-image, …)
- schema or name changes, especially ones that deprecate or rename something (put these under **Changed** and say what the replacement is)
- localization updates (one short line)

**Leave out:**

- Guide and documentation-only commits
- whitespace, indentation, or tab changes; `.git-blame-ignore-revs`
- rebuilt JavaScript/CSS dist files (`JS: update dist files`)
- changes that only touch the sample article, workbook, or other examples
- test-only and internal refactors that don't change output
- removal of unused internal strings

## 4. Write the entries

- Group entries under the `### Added`, `### Fixed`, and `### Changed` headings in `[Unreleased]`. Keep any entries already there (CLI changes) and add a heading only if it is missing.
- Write **one entry per feature**, not one per commit. A feature often spans many commits (publisher variable + assembly + each output format + schema).
- Write for PreTeXt authors: plain language, with element and attribute names in backticks. Say what changed for the user, not what code changed.
- Match the terse, one-sentence-per-item style of earlier releases in `CHANGELOG.md`.

## 5. Report back

Tell the user:

- the commit range you used, and whether `CORE_COMMIT` is current with core's `origin/master`
- a short summary of what you added under each heading
- what you left out, grouped by kind
- any judgment calls worth a second look, especially renames or deprecations that could break existing projects
