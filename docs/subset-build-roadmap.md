# Roadmap: collections (many divisions of one document, each built as its own output)

**Status: Phase 1 is implemented on the `collections` branch (2026-11-23): a `pdf`
or `latex` target with `division="<xml:id>"` builds that one division as its own
document.** SCORM, collections of many divisions, and PreTeXt.Plus are still to do.
The earlier spike is a runnable project in [subset-spike/](subset-spike/).

This replaces the plan of 2026-07-12 (wrap one division in an empty `article` and
build that). The section "What changed from the July plan" records what was dropped
and why.

## Goal

From one PreTeXt document, build a set of outputs, one per chosen division, in a
single target.

- **Weekly exercise sets.** Course materials hold a single-page exercise set for
  each week. A "SCORM collection" target gives one zip holding a SCORM package per
  set, each ready to upload to an LMS so students get credit.
- **Exams and quizzes.** A document holds every exam and quiz for the term. A PDF
  collection target gives one PDF per exam, so page numbers do not run on.

Each piece must look like its own thing: its own title, no title page left over
from the parent document.

It must work in PreTeXt.Plus, which builds through the CLI's Python API
(`Project().new_target(...).build()`) with a publication file. So the feature is
configured by target attributes and the publication file, never by command-line
flags alone.

## Picking this up

State on 2026-11-23, on the `collections` branch:

- Phase 1 is done, with tests that pass against both the pinned core and a core
  checkout at `f560a2b52`. See "Phase 1 as built" below.
- Next is Phase 2, one division as a SCORM package.
- One decision is waiting on Oscar: which elements may be built alone. The answer
  lives in `division_can_stand_alone` in `pretext/utils.py`, marked `TODO(human)`,
  and is a conservative guess for now.

If the CLI reports a missing file under `~/.ptx/<version>/core`, the bundled core is
older than `CORE_COMMIT`: run `uv run python scripts/fetch_core.py`, and
`scripts/symlink_core.py` again if core is linked.

## Phase 1 as built

A target in the manifest, or `Project.new_target(...)` in Python:

```xml
<target name="exam1" format="pdf" division="exam-one"/>
```

- **Where the code is.** The stylesheets ship in `pretext/resources/division/`.
  `utils.copy_division_xsl` places them beside a copy of core's XSL at build time.
  `Target.build` applies them when `division` is set, and `Target.check_division`
  rejects an `xml:id` that is missing or is not a division.
- **Formats.** `latex`, and `pdf` by the `latex` method. Anything else is rejected
  when the target is created.
- **Output name.** `<xml:id>.pdf` or `.tex`, unless `output-filename` is given.
- **Assets.** Only the division's assets are generated, and they are the same files
  the whole document uses.
- **A target's own `xsl`** still applies: the division stylesheet imports it in
  place of core's.
- **Numbers are exact in the PDF**, not only for divisions. See the next section.
- **An article prints no title block**, since the division's heading already shows
  the title.

Tests are in `tests/test_project.py` (search for "division"), using the example
project `tests/examples/projects/division`.

## LaTeX numbering: what core offers, and what Phase 1 does

Oscar recalled talk of core doing the numbering for LaTeX itself. As of core
`f560a2b52` there are two related features, and neither is that switch:

- **`debug.numbering.check`**, a string parameter. Set to `yes`, the LaTeX output
  compares PreTeXt's number with LaTeX's own for every division and block, and
  writes a warning to the LaTeX log on a mismatch. It checks; it does not change
  what is printed.
- **`$b-latex-hardcode-numbers`**, a stylesheet variable that only the solutions
  manual turns on. It prints PreTeXt's number for figures, tables, lists and
  listings. It does not cover headings or theorem-like blocks, so on its own it
  cannot make a single division's PDF right.

The groundwork is there (every number is stamped on the tree during assembly), but
LaTeX still counts for itself. So Phase 1 sets LaTeX's counters from the stamps,
once, where the division begins:

- each ancestor's division counter, to the ancestor's number;
- the division's own counter, to one less than its number;
- the equation counter and each block counter (core has at most five), to one less
  than the number of the first item in the division that uses it.

The numbering check is the test for this. `test_division_pdf_numbers_match` builds
PDFs with the check on and fails on any warning. With the counter setting disabled
the same test fails, so it does detect drift.

Footnote numbers are not handled.

## Decisions (2026-11-22)

1. **The collection is defined on a target in the project manifest.** The
   publication file keeps deciding how each piece looks.
2. **The cut is made in the fully assembled source**, after versions are resolved,
   identifiers assigned, and numbers stamped.
3. **A piece keeps its numbers from the full document by default** ("Worksheet 2.2",
   "Theorem 3.1.2"). Publication settings can already suppress division numbers
   where an author wants none. Restarting at 1 everywhere is not the default.
4. **The document title of a piece is the division's title.** It shows in the HTML
   banner and in the SCORM manifest, so packages are easy to tell apart in an LMS.
   A theme that hides the banner handles the case where no banner is wanted.
5. **CLI only for now.** Moving the cut into core is welcome later but nothing here
   waits on an upstream change.
6. **No new root element and no new converter stylesheet in core.** Splitting is a
   publishing decision, not an authoring structure.

## How it works

Core's assembly ends by stamping numbers onto every numbered element as attributes
(`@pi:struct`, `@pi:serial`, `@pi:level`; the `serial-stamp` pass in
`pretext-assembly.xsl`). The converters read those stamps (`pretext-numbers.xsl`)
and take their input tree from three variables: `$root`, `$docinfo`,
`$document-root`. Core's own comment above those variables says a conversion may
override them, and the braille conversion does.

The CLI supplies a small stylesheet that imports the normal converter and overrides
those three variables with a pruned copy of the final tree:

- `docinfo` is kept whole.
- The document root (`book` or `article`) is kept, with its `title` replaced by the
  division's title.
- Each ancestor between the root and the division is kept as an empty shell: its
  attributes, its title, and only the child that leads to the division.
- The division is copied whole.
- Everything else is dropped.

Keeping the ancestors matters. Core decides many things by `parent::` and
`ancestor::` tests (which LaTeX environment a worksheet uses, how exercises are
numbered), and a division moved directly under the root breaks them.

Two more pieces make the output right:

- **Ancestors render as nothing.** A template in the importing stylesheet matches
  the shell ancestors and only passes through to the division.
- **Cross-references that leave the division** are marked during the copy. When
  rendered, they show their usual text ("Theorem 1.1.1"), worked out from the
  target in the full tree, with no link.

LaTeX needs one extra step, because LaTeX numbers headings and blocks with its own
counters. Each shell ancestor sets its counter to its stamped number, and the
division's counter is set one short of its number.

Because every piece is built from the same unmodified source file, generated assets
are made once for the whole document and shared by all pieces. There is no staged
copy of the source and nothing is assembled twice.

## Spike results (2026-11-22)

Run with the development CLI linked to the core checkout at `f560a2b52`, on a
three-chapter sample book ([subset-spike/source/main.ptx](subset-spike/source/main.ptx))
and an article-rooted copy of it. Pieces tried: two worksheets and a section.

| Check | Result |
|---|---|
| PDF of one worksheet from a book | One page. Heading "2.2 Week 1 Exercises", "Figure 2.2.1", no title page. |
| PDF of one section from a book | "3.1 Exam 1", "Example 3.1.1", "Theorem 3.1.2". |
| Reference to a theorem outside the piece | "Theorem 1.1.1" as plain text in PDF and HTML. A reference inside the piece stays a live link. |
| SCORM package of one worksheet | Builds. Manifest title "Week 1 Exercises", banner and page title the same, heading "Worksheet 2.2 Week 1 Exercises", `index.html` present. |
| Generated image with no `xml:id` | The piece uses the full document's file (`ws-week1-5-2.svg`), so assets are shared. |
| Same tests on an article | Numbers kept. See the title and figure-number gaps below. |

Not checked: loading a package in a real LMS, how the HTML looks in a browser, the
banner-hiding theme, documents with parts, WeBWorK or other server-generated
exercises, and the pinned core (it has the `serial-stamp` pass, but the spike ran
only against the checkout).

## Gaps the spike found

- **PDF block numbers can drift.** *Fixed in Phase 1* by setting LaTeX's counters;
  see "LaTeX numbering" above. When the spike ran, a second worksheet's figure was
  "Figure 2.2" in HTML but "Figure 2.1" in its PDF.
- **An article prints its title twice in PDF.** *Fixed in Phase 1*: the title block
  is switched off.
- **Every SCORM package is about 10 MB**, for a tiny worksheet, and the size does
  not depend on content. Nearly all of it is `_static` (25 MB unzipped), including
  about 9 MB of JavaScript source maps. Fifteen pieces would be about 150 MB.
- **Every package carries every generated asset** of the whole document, because the
  build copies the generated folder whole.
- **Every package has the same manifest identifier**, `ptx-scorm-test`, hard-coded
  in core.
- **Navigation is still on the page**: previous/next buttons and a table of contents
  with two or three entries.
- **Footnote numbers** in a PDF restart, where they would otherwise continue from
  earlier in the document.
- **Only single-target references are handled.** A reference with a list or a range
  of targets that leaves the piece is not marked.
- **A target's own custom stylesheet.** *Fixed in Phase 1*: the division stylesheet
  imports it.
- **The approach leans on core internals**: the `$serial-stamp` variable, the
  `pi:` stamps, and the override of `$root`. Core documents the override, but a
  rename upstream would break this silently. The Phase 1 tests guard against
  that, and should be run whenever `CORE_COMMIT` moves.

## Configuration

One division, as built in Phase 1:

```xml
<target name="exam1" format="pdf" division="exam-one"/>
```

Many divisions, a sketch for Phase 3 with names still open:

```xml
<target name="assignments" format="html" compression="scorm"
        publication="publication-scorm.ptx" collection="worksheet"/>
<target name="exams" format="pdf" collection="#exam1 #exam2 #quiz1"/>
```

`collection` names either kinds of division (every `worksheet`) or individual
divisions by `xml:id`. In PreTeXt.Plus the same value is passed to
`new_target(...)`.

Output: `output/<target>/<name>.<ext>` for each piece, plus one bundle zip of them
all.

## Phases

1. **One piece, PDF.** *Done 2026-11-23.* See "Phase 1 as built".
2. **One piece, SCORM.** Per-piece manifest identifier. Decide what to do about
   navigation and package size (see open questions).
3. **Collections.** The `collection` attribute and its schema entry, the loop over
   pieces with one shared asset pass, file naming, the bundle zip.
4. **PDF number fidelity.** *Done in Phase 1*, except footnotes.
5. **PreTeXt.Plus.** Expose the collection target in the build service.
6. **Documentation.** Guide section and CHANGELOG entry.
7. **Later, upstream.** Move the pruning into core's assembly as a real pass, with
   the shell ancestors and literal LaTeX numbers handled there. The CLI stylesheets
   then shrink to nothing.

## Open questions

- Package size: strip source maps, drop unused scripts, or rely on a portable build
  that loads scripts from a CDN? Does an LMS allow the CDN route?
- Should a piece carry only the generated assets it uses?
- File names: `xml:id`, or a name made from the title?
- Should outward references link to a deployed copy of the full book when the
  publication file gives a base URL?
- What may be a piece? Phase 1 allows `chapter`, `section`, `subsection`,
  `subsubsection`, `worksheet`, `handout`, `exercises` and `reading-questions`.
  Parts, appendices and other back matter, and blocks such as a single `exercise`
  or `project`, are refused for now. This is Oscar's call
  (`division_can_stand_alone`).
- Does the existing `-x` option keep its present meaning?

## What changed from the July plan

| July 2026 | Now | Why |
|---|---|---|
| Extract the division, wrap it in an empty `article` or `book`, build that as a new document | Prune the assembled tree inside the conversion, keeping the real root and ancestors | Numbers are stamped during assembly from position, so a new document always restarts at 1. Keeping numbers is now the default. |
| Stage a copy of the source and a derived publication file | Build from the original source file | No second assembly, so the old plan's main risk is gone, and assets are shared. |
| Standalone numbering; `chapter-start` for chapters | Numbers from the full document | Decision 3. |
| Outward references become the target's title | Outward references show their normal text, unlinked | The full tree is available at render time. |
| Empty wrapper title, except SCORM and zip | Division title is the document title | Decision 4. The article PDF case still needs the title suppressed. |
| Strict containment: only divisions that fit directly in an `article` or `book` | Any division, since its ancestors stay | Follows from keeping the ancestors. |
| Three entry points: `-x`, a division file as target, manifest attributes | Manifest target attribute first | PreTeXt.Plus cannot use command-line flags. |
