# Roadmap: tagged/accessible PDF via LaTeX's native `\DocumentMetadata`

**Status: paused after a feasibility spike (2026-08-30). Nothing has been implemented
yet — this document exists so the investigation doesn't have to be redone.**

## Motivation

[PreTeXtBook/pretext#1046](https://github.com/PreTeXtBook/pretext/issues/1046)
("Investigate accessibility improvements for LaTeX/PDF output", opened 2019) was
reopened 2026-08-05: PreTeXt's accessible-PDF effort has so far landed as the
**XSL-FO/Apache FOP** converter (`xsl/pretext-fo.xsl` in core, see core's
`doc/pretext-fo-roadmap.md`), which produces PDF/UA-1-conformant output verified
with veraPDF. That route is capped — its own roadmap lists "PDF/UA-2 and MathML
association are beyond FOP today" under *Saved for later*. Issue #1046 asks what
the **LaTeX** route itself can now offer as a companion or fallback, since the
LaTeX Project's native tagging machinery (`\DocumentMetadata`) has matured a lot
since 2019/2020 (when only third-party packages like `axessibility`/`pdfx` existed).

That maturity is recent and real: as of the **2025-11-01 LaTeX2e kernel release**,
tagging is no longer a prototype/testphase feature — it's usable in production
with a single `\DocumentMetadata{tagging=on}` declaration before `\documentclass`,
and **LuaLaTeX is the preferred engine** (best MathML/math support; also works,
with more manual math work, under pdfLaTeX).

## Two things make this non-trivial

1. **`lualatex` is currently a dead option in pretext-cli.** It exists as a
   `PdfMethod` enum value (`pretext/project/xml.py`) but was added preemptively
   during an unrelated refactor (the `pdf-fo` work) and is wired nowhere else —
   selecting it today crashes with a raw `KeyError`. See "Engine plumbing gap"
   below.
2. **Package compatibility with tagging is uneven**, and PreTeXt's LaTeX output
   leans hard on `tcolorbox`, whose `listings`-highlighting mode turns out to
   conflict with tagging. See "Phase 0 findings" below — this is the concrete,
   scoped blocker discovered so far.

## Engine plumbing gap (facts, as of 2026-08-30)

- `PdfMethod.LUALATEX` exists (`xml.py`) but `LatexEngine` (used for
  `latex-image` asset rendering) does **not** have a `LUALATEX` member.
- `Executables` (`xml.py`) — whose `.model_dump()` becomes the executable-lookup
  dict via `core.set_executables()` — has no `lualatex` field, so
  `common.get_executable_cmd("lualatex")` (core repo, `pretext/lib/common.py`)
  does a plain `dict["lualatex"]` lookup that raises `KeyError`.
- Core's `pretext.cfg` `[executables]` section also has no `lualatex =` entry.
- `schema/project-ptx.rnc` doesn't even permit the string `"lualatex"` for
  `pdf-method`/`latex-engine` — schema and Python enum have drifted.
- `pretext/utils.py`'s executable pre-flight check (`check_asset_execs`)
  hardcodes `"xelatex"` regardless of configured engine.
- No `HAS_LUALATEX` test-skip guard exists (only `HAS_XELATEX`,
  `tests/common.py`), and `test_executables_match_core`
  (`tests/test_project.py`) hardcodes the current executable-key set, so it
  would need updating.

**The generated `.tex` is already engine-agnostic, by design** — this part is
*not* a gap. `latex-engine-support` and `font-support` (core repo,
`xsl/pretext-latex-common.xsl`) branch at **LaTeX-compile time** via
`\ifthenelse{\boolean{xetex} \or \boolean{luatex}}`, added in 2016 (PR #337).
The same `.tex` file already compiles under pdflatex/xelatex/lualatex without
XSL changes. One pre-existing comment claimed *"LuaTeX is not tested nor
supported"* for the `tcolorbox`+`listings` integration
(`pretext-latex-common.xsl`, near the program-listing setup) — the Phase 0
spike below shows plain lualatex compilation actually works fine; the real
problem is narrower (see below).

Where `\DocumentMetadata` would need to be injected: it must be the literal
first content of the `.tex` file (comment lines before it are harmless). The
natural point is immediately before each of the four duplicated
`\documentclass[...]` emissions in core's `xsl/pretext-latex.xsl` — `article`,
`book`, `letter`, `memo` templates — which already duplicate their shared
setup lines verbatim (that file has a standing `<!-- TODO: combine article,
book, letter templates -->`), so a new duplicated `call-template` line in each
would match the existing pattern, not cut a corner.

A publisher-variable toggle (e.g. `tagged-pdf="yes"` on the `<latex>` element
of a publication file) should mirror the existing `draft` toggle:
`publisher-variables.xsl`'s `pi:pub-attribute name="draft"` →
`$latex-draft-mode` → `$b-latex-draft-mode`, plus the matching
`attribute draft { "yes" | "no" }?` in core's `schema/publication-schema.rnc`.

## Phase 0 findings (feasibility spike, 2026-08-30)

Spiked against the real 208-page `sample-book` project from `pretext-testing`
(an abstract-algebra text with proofs, exercises, code, an index — not a toy
document), using a local TeX Live 2026 install (lualatex already present,
well past the 2025-11-01 tagging-capable kernel).

**Works cleanly:**
- Plain `lualatex` compile of the full book, no `\DocumentMetadata` at all:
  succeeds, 208 pages, no fatal errors. This refutes the stale "untested"
  comment mentioned above, at least for general compilation.
- With `\DocumentMetadata{lang=en,tagging=on}` prepended: everything PreTeXt
  renders via plain `\newtcolorbox` — theorem, proof, example, remark,
  exercise, figure, table environments, i.e. the structural backbone of a
  typical math/CS book — compiles cleanly under tagging. Confirmed two ways:
  the real book got through ~14 pages of exactly this content before hitting
  the failure below, and an isolated minimal reproduction (a `\newtcolorbox`
  theorem environment, tagging on) compiles to a 1-page tagged PDF with no
  errors.

**Blocked:**
- `<program>`/`<console>`/Sage code blocks use `\newtcblisting` (tcolorbox's
  `listings`-highlighting mode, distinct from plain `\newtcolorbox`). Under
  tagging this is a **fatal** error, not a warning:

  ```
  ! Package tagpdf Error: The number of automatic begin (5) and end (6)
  (tagpdf)                text-unit para hooks differ!
  ```

  Minimal reproduction (6 lines, fails the same way):

  ```latex
  \DocumentMetadata{lang=en,tagging=on}
  \documentclass{article}
  \usepackage[most]{tcolorbox}
  \newtcblisting{program}[1]{listing options={language=#1}}
  \begin{document}
  \begin{program}{python}
  print("hello")
  \end{program}
  \end{document}
  ```

  Tried the standard `\tagpdfparaOff` / `\tagpdfparaOn` escape hatch around
  the environment — it changed the imbalance (5 vs 4 instead of 5 vs 6) but
  did not fix it. tcolorbox's listings mode does its own internal
  paragraph/box bookkeeping (it measures content twice for auto-sizing) that
  doesn't line up with tagpdf's automatic paragraph tagging. This matches
  community reports that `listings`-family integrations are a known trouble
  spot for the LaTeX tagging project.

**Net effect**: any PreTeXt document containing code listings currently
cannot compile with tagging on. Everything else — prose, math, theorems,
tables, images, index, cross-references — can. This is a scoped,
identifiable gap, not a fundamental blocker to the whole approach.

Local validation tooling note: veraPDF (used by the FOP route's roadmap doc
via `verapdf --flavour ua2`/`ua1`) was not available in the spike environment,
so PDF/UA conformance itself hasn't been checked yet — only that lualatex
compiles without fatal errors and produces a tagged PDF (`tagpdf` logs
confirm it writes `StructTreeRoot`, `ParentTree`, etc.).

## Proposed path forward (not started)

1. **Resolve the `tcblisting` blocker** — either find/apply an upstream fix
   (check the `latex3/tagging-project` and `tcolorbox` issue trackers for
   this specific "para hooks differ" failure), or give PreTeXt's tagging
   branch a non-tcolorbox code-display fallback (e.g. plain `fancyvrb`/
   `listings` without the tcolorbox box-measuring wrapper) for `<program>`/
   `<console>`/Sage content specifically. Until one of these lands, `tagged-pdf`
   support should refuse (with a clear message) or warn-and-continue on
   documents containing code listings, rather than silently producing a
   broken build.
2. **Wire `lualatex` as a first-class engine** (independent value regardless
   of the tagging outcome — closes a pre-existing gap):
   - `pretext/project/xml.py`: add `lualatex` to `Executables`; add
     `LUALATEX` to the `LatexEngine` enum.
   - core repo `pretext/pretext.cfg`: add `lualatex = lualatex`.
   - `schema/project-ptx.rnc` (+ regenerate `.rng` via `trang`): allow
     `"lualatex"` for `pdf-method`/`latex-engine`.
   - `pretext/utils.py`: generalize the hardcoded `"xelatex"` pre-flight
     check.
   - `tests/common.py`: add `HAS_LUALATEX`, mirroring `HAS_XELATEX`; update
     `test_executables_match_core`.
   - Bump `CORE_COMMIT` (`pretext/__init__.py`) once the core-repo change
     lands.
3. **Opt-in tagged-PDF preamble**: `tagged-pdf` publication attribute (core
   repo `schema/publication-schema.rnc`, `xsl/publisher-variables.xsl`), and
   a `latex-document-metadata` XSL template (core repo
   `pretext-latex-common.xsl`/`pretext-latex.xsl`) that emits
   `\DocumentMetadata{...}` before `\documentclass` when the toggle is on and
   the engine is lualatex/pdflatex. Warn and skip (not silently ignore) if
   the engine doesn't support tagging.
4. **Alt-text wiring (stretch)**: wire the `<description>` PreTeXt already
   authors for HTML `alt` text into `\includegraphics`'s `alt=` key, only
   inside the tagging-on branch.
5. **Testing & CI**: a pytest fixture with `pdf-method="lualatex"
   tagged-pdf="yes"`, gated by `HAS_LUALATEX`; a veraPDF validation step
   (`--flavour ua2` or whatever proves realistic) that reports rather than
   hard-fails initially, given the partial-compatibility landscape; a
   `pretext-testing` fixture + snapshot once stable.
   Also: the two Docker images that gate real builds —
   `pretextbook/pretext-full:latest` (CI `deep-test` job, devcontainer) and
   `oscarlevin/pretext-full` (end-user template workflow) — need a TeX Live
   2025-11+ scheme with lualatex before this can be exercised in CI or by
   end users generated projects. Neither image's TeX Live version is known
   from these repos; check before relying on either.

## Package compatibility notes (from `latex3/tagging-project`'s tagging-status
page, checked 2026-08-30)

`hyperref` foundational/fine; `xcolor`, `array`, `booktabs`, `calc`,
`environ` compatible; `amsmath`/`amssymb`/`amsthm`/`enumitem`
partially-compatible (documented open issues); `caption`
currently-incompatible (float configuration gets overwritten by tagging);
`biblatex` partially-compatible (needs `hyperref`, which PreTeXt already
loads); `babel` unchecked-but-likely-fine. `tcolorbox`'s plain mode tested
fine in Phase 0 above; its `listings` mode is the confirmed blocker.
