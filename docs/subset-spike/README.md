# Collections spike

A runnable PreTeXt project that proves the approach in
[../subset-build-roadmap.md](../subset-build-roadmap.md): build one division of a
book as its own PDF or SCORM package, keeping the numbers it has in the full book.

This is the first proof of the idea, kept for reference. The CLI now does this
itself for PDF and LaTeX, through a target's `division` attribute, with improved
versions of these stylesheets in `pretext/resources/division/`. The HTML and SCORM
stylesheet here is still the only one of its kind.

Nothing here is wired into the CLI. Each "piece" target in `project.ptx` uses the
existing custom-stylesheet hook (`xsl=`) and a `subset.id` string parameter.

## Files

- `source/main.ptx`: a three-chapter book with two worksheets (`ws-week1`,
  `ws-week2`), two sections used as exams (`exam1`, `exam2`), a reference from a
  worksheet to a theorem in another chapter, and generated images with no `xml:id`.
- `xsl/subset-common.xsl`: prunes the assembled tree to the chosen division and
  handles references that leave it. Shared by both formats.
- `xsl/subset-latex.xsl`, `xsl/subset-html.xsl`: import the normal converter,
  include the common file, and make the shell ancestors render as nothing. The
  LaTeX one also seeds LaTeX's counters.

## Run it

From this directory, with the development CLI (see the repository `AGENTS.md`):

    uv run --project ../.. pretext build ws1-pdf
    uv run --project ../.. pretext build ws1-scorm
    uv run --project ../.. pretext build exam1-pdf
    uv run --project ../.. pretext build full-pdf      # the whole book, to compare

Results land in `output/<target>/`. Expect "2.2 Week 1 Exercises" and
"Theorem 1.1.1" in `ws-week1.pdf`, and "3.1 Exam 1" in `exam1.pdf`.

The spike was run with core linked to a checkout at `f560a2b52`. It has not been
run against the pinned core.
