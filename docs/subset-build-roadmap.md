# Roadmap: collections (many divisions of one document, each built as its own output)

**Status: design chosen and proven by a spike on 2026-11-22. Nothing is implemented
in the CLI yet.** The spike is a runnable project in
[subset-spike/](subset-spike/); its README says how to build it.

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

State on 2026-11-23: this roadmap and the spike are the only work. They are on the
`collections` branch. No CLI code has changed.

1. Rebuild the spike to confirm the environment
   ([subset-spike/README.md](subset-spike/README.md)). If the CLI reports a missing
   file under `~/.ptx/<version>/core`, the bundled core is older than `CORE_COMMIT`:
   run `uv run python scripts/fetch_core.py`, and `scripts/symlink_core.py` again if
   core is linked.
2. Answer the one question left open: should exact PDF numbers be fixed in Phase 1
   (seed block counters), or accepted as a known gap until the cut moves into core?
3. Start Phase 1 below.

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

- **PDF block numbers can drift.** When a counter runs across sibling divisions, the
  PDF restarts it. In the article, the second worksheet's figure is "Figure 2.2" in
  HTML (correct) but "Figure 2.1" in its PDF. Seeding division counters is not
  enough; block counters need seeding too, or core needs to write those numbers
  literally. Its existing switch for that (`$b-latex-hardcode-numbers`) does not
  cover headings or theorem-like blocks.
- **An article prints its title twice in PDF.** The `article` template calls
  `\maketitle` whenever there is a title and no title page, so the piece shows the
  title block and then the division heading. A book does not. The PDF route should
  leave the root title out, or suppress `\maketitle`.
- **Every SCORM package is about 10 MB**, for a tiny worksheet, and the size does
  not depend on content. Nearly all of it is `_static` (25 MB unzipped), including
  about 9 MB of JavaScript source maps. Fifteen pieces would be about 150 MB.
- **Every package carries every generated asset** of the whole document, because the
  build copies the generated folder whole.
- **Every package has the same manifest identifier**, `ptx-scorm-test`, hard-coded
  in core.
- **Navigation is still on the page**: previous/next buttons and a table of contents
  with two or three entries.
- **Only single-target references are handled.** A reference with a list or a range
  of targets that leaves the piece is not marked.
- **A target's own custom stylesheet** is not combined with the pruning stylesheet
  yet. The pruning stylesheet would need to import the author's file, not core's.
- **The approach leans on core internals**: the `$serial-stamp` variable, the
  `pi:` stamps, and the override of `$root`. Core documents the override, but a
  rename upstream would break this silently. A test that builds one piece and
  checks a number guards against that.

## Configuration (sketch; names are open)

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

1. **One piece, PDF.** Ship the pruning stylesheets with the CLI. Add a way for a
   target to build a single division through them. Fix the article title. Test that
   pins a heading number and an outward reference.
2. **One piece, SCORM.** Per-piece manifest identifier. Decide what to do about
   navigation and package size (see open questions).
3. **Collections.** The `collection` attribute and its schema entry, the loop over
   pieces with one shared asset pass, file naming, the bundle zip.
4. **PDF number fidelity.** Seed block counters, or agree a core change.
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
- What may be a piece? The spike used worksheets and a section. Chapters should
  work the same way. Anything that is not a division needs thought.
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
