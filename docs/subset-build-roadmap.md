# Roadmap: collections (many divisions of one document, each built as its own output)

**Status: Phases 1 to 3 are implemented on the `collections` branch (2026-11-23).
A target with `division="<xml:id>"` builds one division as its own PDF, LaTeX file,
HTML page, or SCORM package, and a target with `collection="..."` builds many of
them at once.** PreTeXt.Plus and documentation are still to do. The earlier spike
is a runnable project in [subset-spike/](subset-spike/).

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

- Phases 1 to 3 are done, with tests that pass against both the pinned core and a
  core checkout at `f560a2b52`. See the three "as built" sections.
- Next is Phase 5, exposing a collection target in the PreTeXt.Plus build service,
  and Phase 6, the Guide.
- No package has been loaded into a real LMS yet. That is the check most worth
  doing before anyone relies on this.
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
- **Formats.** `latex`, and `pdf` by the `latex` method. (Phase 2 added `html`.)
  Anything else is rejected when the target is created.
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

## Phase 2 as built

```xml
<target name="week1" format="html" compression="scorm" division="ws-week-one"/>
```

- **Formats.** `html`, with or without `compression`, but not on the Runestone
  platform. Without `compression` the output is a directory, as for any HTML
  target, which is the easy way to look at a division in a browser.
- **One page.** The division is a single page whatever chunking the publication
  file sets, with no table of contents, no search, and no previous, next or up
  buttons. The stylesheet is `cli-division-html.xsl`.
- **Package name.** `<xml:id>.zip`, unless `output-filename` is given.
- **The CLI makes the zip itself**, where core would otherwise
  (`Target._build_division_package`, `utils.package_division_html`). That is where
  the next two points happen.
- **Manifest identifier.** `ptx-<document>-<division>`, where the document is
  named by `docinfo/document-id`, else the root's `xml:id`, else the source file
  name. It is the same on every build.
- **Size.** About 2 MB for the test worksheet, down from 10 MB. Files in `_static`
  that do nothing in a package are left out: JavaScript source maps, and the
  compressed twin (`x.js.gz`) of any file that is also there uncompressed. Those
  were 18 of the 25 MB.
- **Checked in a browser:** the trimmed package opens from `index.html`, its
  multiple-choice exercise grades, the SCORM script starts and counts the gradable
  questions, and there are no script errors.

Not done, on purpose: **generated assets are not pruned.** A package carries the
whole generated folder. Finding the files a page uses by scanning it is unsafe,
because core's WeBWorK script builds those paths in JavaScript. A project whose
other divisions have never been built only has the division's own assets, so the
problem shows up in projects that also build the whole document.

## Phase 3 as built

The two user stories, as targets:

```xml
<target name="assignments" format="html" compression="scorm"
        collection="worksheet" output-filename="assignments.zip"/>
<target name="exams" format="pdf" collection="#exam1 #exam2 #final"/>
```

- **What `collection` holds.** Words separated by spaces. A plain word is a kind
  of division, and selects every one that has an `xml:id`. A word starting with
  `#` is the `xml:id` of one division. They can be mixed; a division selected
  twice is built once. Divisions are built in document order.
- **Each division is built as `division` would build it**, and named
  `<xml:id>.pdf`, `.tex` or `.zip`. Uncompressed HTML is a directory, so each
  division gets a directory named for it.
- **One zip of everything** is made when the target has an `output-filename`,
  which names that zip. The individual outputs stay beside it. Without an
  `output-filename` there is no zip, only the individual outputs.
- **Refused, before anything is built:** a `#` id that does not exist or is not a
  division; a kind that selects nothing; a zip name equal to one of the outputs;
  `collection` together with `division`; a standalone target.
- **A division with no `xml:id`** cannot be selected by kind, since there is
  nothing to build it by or name it with. It is skipped with a warning that gives
  its title.
- **Work done once, not per division:** parsing and checking the source, cleaning
  the output, and generating assets (for the whole document).
- **Where the code is.** `Target.collection_divisions` picks the divisions,
  `Target._build_collection` loops, `Target._piece_target` makes the copy of the
  target that builds one division, and `utils.bundle_collection` makes the zip.

Known cost: **each division is a full conversion of the whole document.** The cut
happens inside the conversion, so forty worksheets means forty passes of core's
assembly over the book. On the small test book a SCORM package takes about three
seconds. On a large book this will be slow, and is the main reason to move the
cut into core eventually, where one pass could write every division.

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
- **Every SCORM package is about 10 MB.** *Fixed in Phase 2*: about 2 MB, by
  leaving out source maps and compressed duplicates.
- **Every package carries every generated asset** of the whole document, because the
  build copies the generated folder whole. *Still open*; see "Phase 2 as built".
- **Every package has the same manifest identifier.** *Fixed in Phase 2.*
- **Navigation is still on the page.** *Fixed in Phase 2.*
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

All of this is built; see the "as built" sections for details.

```xml
<!-- one division -->
<target name="exam1" format="pdf" division="exam-one"/>

<!-- many divisions, and a zip of them all -->
<target name="assignments" format="html" compression="scorm"
        collection="worksheet" output-filename="assignments.zip"/>
```

In Python, as PreTeXt.Plus would use it:

```python
target = project.new_target(
    "assignments", "html", compression="scorm",
    collection="worksheet", output_filename="assignments.zip",
)
target.build()
```

## Phases

1. **One piece, PDF.** *Done 2026-11-23.* See "Phase 1 as built".
2. **One piece, SCORM.** *Done 2026-11-23.* See "Phase 2 as built".
3. **Collections.** *Done 2026-11-23.* See "Phase 3 as built".
4. **PDF number fidelity.** *Done in Phase 1*, except footnotes.
5. **PreTeXt.Plus.** Expose the collection target in the build service.
6. **Documentation.** Guide section and CHANGELOG entry.
7. **Later, upstream.** Move the pruning into core's assembly as a real pass, with
   the shell ancestors and literal LaTeX numbers handled there. The CLI stylesheets
   then shrink to nothing.

## Open questions

- Should a piece carry only the generated assets it uses? It needs a way to know
  them that does not depend on scanning the page.
- Should ordinary SCORM and zip targets get the same size trimming? It is safe for
  them too, but changes what an existing target produces.
- Should a long division, a chapter say, keep a table of contents for its own
  sections?
- File names: `xml:id` for now. Would a name made from the title be better for
  an LMS upload dialog?
- Should a collection write an index (CSV or JSON) listing each division's
  `xml:id`, title and file, for bulk upload or for PreTeXtHub?
- Should a division with no `xml:id` be buildable, under a name the CLI makes up?
- Should a collection generate assets only for its divisions? One pass over the
  whole document is simple, but wasteful for three exams out of a large book.
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
