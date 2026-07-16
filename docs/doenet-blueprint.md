# Blueprint: a first-class `<doenet>` element for PreTeXt

Status: draft plan, 2026-07-16. Nothing here is implemented yet.

## 1. Goal

Let an author drop a Doenet question into a PreTeXt document the same way a
`.pg` file is dropped into a `<webwork>` element:

```xml
<exercise xml:id="ex-average-velocity">
  <title>Finding average velocity from data</title>
  <introduction>
    <p>Optional PreTeXt context, melded into the statement.</p>
  </introduction>
  <doenet>
    <xi:include parse="text" href="problems/average-velocity.doenet"/>
  </doenet>
</exercise>
```

A generation step (`pretext generate doenet`) converts each question into a
per-question representations file containing both the **dynamic** part (the
DoenetML source itself) and a **static** PreTeXt part produced locally by the
[`doenetml-to-pretext`](https://pypi.org/project/doenetml-to-pretext/) PyPI
package. HTML output stays live and interactive; PDF/EPUB/braille get the
static form melded in automatically.

This replaces the current, hand-maintained approaches:

- a bare `interactive[@platform='doenetml']` + `slate[@surface='doenetml']`
  (no automatic static form — falls back to QR code / screenshot), and
- the experimental "dual" exercise where the author writes *both*
  `<dynamic>` (holding the interactive) and `<static>` by hand
  (see `examples/sample-book/rune.xml`, exercise "doenet-velocity",
  marked "strictly EXPERIMENTAL" 2025-11-05).

### Decisions already made (2026-07-16)

1. **Placement**: `<doenet>` is allowed only as the interactive-question child
   of `exercise` and the PROJECT-LIKE elements (`project`, `activity`,
   `exploration`, `investigation`) — same slots as `webwork`/`stack`/
   `myopenmath`. Standalone applets keep using `interactive` + `slate`.
2. **HTML builds do not require generation.** HTML renders the live applet
   directly from the DoenetML text already in the source tree (post-xinclude).
   The reps file is required only for static formats — the STACK model, not
   the strict webwork model. *Addition:* an opt-in, webwork-style
   **activate button** mode for HTML, which shows the static representation
   until the reader clicks to load the live applet (this mode does consume
   the reps file).
3. **Runestone/SCORM**: `exercise/doenet` renders as the (experimental)
   gradeable **dual** component (`data-component="dual"`), synthesized
   automatically instead of hand-authored.
4. **PreFigure chain wired up in v1**: Doenet graphs convert to PreFigure
   images in the static rep; v1 must carry those all the way into a PDF.

## 2. The converter package (verified 2026-07-16, v0.7.21)

`pip install doenetml-to-pretext` (AGPL-3.0). Facts established by inspecting
the wheel and running conversions:

- API: `convert_doenetml_to_pretext(str) -> str` and, importantly,
  `convert_multiple_doenetml_to_pretext(list[str]) -> list[str]`. Each call
  spawns a **Deno** subprocess (`deno eval` on a bundled ~18 MB JS bundle), so
  the batch call is the one to use — one Deno startup for the whole book.
- Deno is *not* installed by pip; the package looks for the `deno` pip
  package first, then `PATH`.
- Single conversion returns a standalone document
  (`<?xml ...?><pretext><article>…`). The batch call runs in *fragment mode*
  and returns embeddable fragments. Observed fragment shapes:
  - DoenetML with a `<problem>` wrapper →
    `<problem xml:id="fragment0-doenet-id-1"><statement>…</statement><solution>…</solution></problem>`
  - bare content → e.g. `<p>Type <m>x</m>: <fillin characters="8"/></p>`
- Answer inputs become `<fillin>` (math answers as `<m><fillin …/></m>`).
- `<graph>` becomes `<image><prefigure xmlns="https://prefigure.org" label="prefigure-doenet-id-9">…</prefigure></image>` — real PreFigure source.

### Known converter issues (verify / file upstream at Doenet/DoenetML)

1. **Solution content dropped**: `<solution><p>It is 4.</p></solution>`
   converted to an empty `<solution/>` in my test. Needs a minimal repro and
   an upstream issue; the melding code should tolerate empty components.
2. **Generated ids collide across questions**: fragments carry
   `xml:id="fragmentN-doenet-id-M"` and `label="prefigure-doenet-id-M"`.
   Two questions converted in separate runs both get `fragment0-…`. Our
   extraction step must rewrite every generated `xml:id`/`label` with the
   question's assembly-id as prefix (also gives PreFigure outputs stable,
   unique filenames).
3. **Deno "byonm" gotcha**: if any ancestor of Deno's cwd contains a
   `package.json` (converter runs with cwd = its site-packages dir, so e.g. a
   `package.json` in `C:\Users\<name>\` when the venv lives under the home
   dir), Deno switches to bring-your-own-node_modules mode and the conversion
   dies with "Could not find a matching package for 'npm:react@…'".
   Workaround verified: a `deno.json` with `{"nodeModulesDir": "none"}` next
   to the bundled JS. Upstream fix: the package should ship that `deno.json`
   (or pass `--node-modules-dir=none`). Until fixed, our core code should
   detect this error string and print a useful hint.
4. **First run needs the network** (Deno fetches `npm:react` into its cache);
   subsequent runs are offline. Document this.
5. Converter version (`0.7.x`, in lockstep with `@doenet/doenetml`) vs the CDN
   version selected by `docinfo/doenetml/@version` for the live applet: the
   extraction should log a warning when they differ materially.

## 3. Architecture

Mirrors STACK (`pretext/lib/stack.py`, `xsl/extract-stack.xsl`) for the
pipeline shape and webwork for the authoring ergonomics. All file references
below: **core** = `PreTeXtBook/pretext` (local: `../pretext`), **CLI** = this
repo.

```
author source          extraction (pretext generate doenet)         consumption
--------------         ------------------------------------         -----------
<exercise>             extract-doenet.xsl dumps                     HTML: live applet synthesized
  <doenet>               (assembly-id, doenetml text)                 from in-tree text (no reps
    xi:include   ───►    for each exercise/doenet          ───►       needed); optional activate-
  </doenet>            lib/doenet.py batch-converts via              button mode uses static rep
</exercise>            convert_multiple_doenetml_to_pretext,        Runestone: dual component
                       post-processes, writes                       PDF/EPUB/braille: static rep
                       generated/doenet/{assembly-id}.ptx             melded by assembly
```

### 3.1 Reps file format (one file per question, root `doenet-reps`)

`generated/doenet/{assembly-id}.ptx`:

```xml
<doenet-reps version="1" doenetml-to-pretext="0.7.21">
  <dynamic><![CDATA[ ...the DoenetML source, verbatim... ]]></dynamic>
  <static>
    <statement>…converted PreTeXt…</statement>
    <hint>…</hint>      <!-- when present -->
    <answer>…</answer>  <!-- when present -->
    <solution>…</solution>
  </static>
</doenet-reps>
```

Per-question files (STACK model) rather than one big
`webwork-representations.xml`: fits the existing `document()` melding
pattern, and partial regeneration stays cheap. `<dynamic>` makes the file
self-contained per the original design intent, even though HTML normally
reads the text straight from the source tree.

Normalization performed by `lib/doenet.py` when building `<static>`:

- If the fragment is a `<problem>`: map its `statement`/`hint`/`solution`
  children into place; drop the `<problem>` wrapper.
- If the fragment is bare content (`<p>`, …): wrap it in `<statement>`.
- Rewrite all converter-generated `xml:id` and `label` values with the
  question's assembly-id prefix (uniqueness + stable PreFigure filenames).
- Drop empty components (`<solution/>`) rather than melding empty blocks.

## 4. Core changes (`PreTeXtBook/pretext`), file by file

### 4.1 Schema — `schema/pretext.rnc` (+ generated .rng, pretext.xml)

- New `Doenet = element doenet { text }` (text content only in v1; a
  `@source` attribute pointing at an external file is a possible follow-up,
  as is `@seed`/variant selection — the converter currently offers no seed
  control).
- Add `Doenet` beside the `WebWork`/`myopenmath` alternatives in the content
  models for `exercise` and PROJECT-LIKE. Note: `<stack>` (the question, not
  the sidebyside layout element of the same name!) is not in the schema yet;
  adding `Doenet` should not wait on that, but watch for the name-collision
  precedent — `doenet` has no collision.

### 4.2 New `xsl/extract-doenet.xsl`

Modeled on `extract-stack.xsl` but emitting XML, not a filename list (the
question body is in-tree text, not an `@source` path):

- imports `publisher-variables.xsl`, `pretext-assembly.xsl`,
  `pretext-common.xsl`, `extract-identity.xsl`
- sets `<xsl:variable name="b-extracting-doenet" select="true()"/>`
- `xsl:output` with `cdata-section-elements` so DoenetML text survives
- for each `exercise/doenet | project/doenet | …` in `mode="extraction"`,
  emit `<question assembly-id="…">{text content}</question>` into one
  ephemeral XML document that `lib/doenet.py` reads.

### 4.3 `xsl/pretext-assembly.xsl`

- Register `b-extracting-doenet` (default `false()`) in the extraction-flag
  block (~line 339) and OR it into `$b-extracting`.
- Classification (~line 1537, next to `stack`): `<xsl:when test="doenet">`
  → `@exercise-interactive = 'doenet'`. This runs in the *exercise* pass
  (pass 5), before representations (pass 8) — same as webwork/stack.
- Representations pass, `$exercise-style = 'static'` branch: clone the STACK
  melding template (~line 2319) for `@exercise-interactive = 'doenet'`:
  read `generated/doenet/{assembly-id}.ptx` via `document()`, meld
  `introduction` + `static/statement` + `conclusion` into `<statement>`,
  copy `static/hint|answer|solution`, re-tag `@exercise-interactive` as
  `static`. Guard with `not($b-extracting)` exactly as STACK does.
- Representations pass, dynamic branch: **synthesize** the structure the
  downstream conversions already understand —

  ```xml
  <dynamic>
    <statement>
      <interactive platform="doenetml" width="100%" aspect="…">
        <slate surface="doenetml">…text content of doenet…</slate>
      </interactive>
    </statement>
  </dynamic>
  <static>…from reps file, when it exists…</static>
  ```

  Because the synthesized node is a genuine
  `interactive[@platform='doenetml']`, the existing HTML machinery
  (`pretext-html.xsl` ~10023–10420: SCORM/Runestone `data-component`
  handling, CDN header libraries keyed to `$docinfo/doenetml/@version`,
  slate rendering ~10824) applies with **zero new rendering code** for the
  always-live path. The `<static>` half is included only when the reps file
  exists; nothing in plain-HTML rendering depends on it.
- Attribute passthrough: honor optional `@aspect`/`@width` on `<doenet>` when
  synthesizing the `interactive` (defaults: `width="100%"`, no aspect →
  existing interactive defaults).

### 4.4 `xsl/pretext-runestone.xsl`

Extend the dual template (`*[@exercise-interactive = 'dual']`, ~line 2117)
to also match `'doenet'`, or simply have the synthesis above re-classify to
`'dual'` when `$b-host-runestone` — preference: extend the match, keep the
classification honest. The template only consumes
`statement/p | statement/interactive[1]` from the dynamic half, which the
synthesis provides.

### 4.5 HTML activate-button mode (opt-in, phase 3)

Webwork's model: publisher variables decide static-vs-live per context;
`pretext-webwork.js` swaps a static rendering for the live problem on click.
For doenet:

- New publisher entries (in `xsl/publisher-variables.xsl` +
  `schema/publication-schema.rnc`), e.g.
  `html/doenet/@activate = "immediate" | "ondemand"` (default `immediate`;
  a per-context split like webwork's `@inline`/`@divisional`/… can come
  later if wanted).
- In `ondemand` mode, HTML renders the static rep (from the reps file — this
  mode *does* require generation, and the build should warn when the file is
  missing and fall back to `immediate`) plus an "Activate" button; JS calls
  `window.renderDoenetViewerToContainer(el)` for that container on click.
- **Pre-existing bug to fix while in here**: the current header script
  (`pretext-html.xsl` ~10417) runs
  `renderDoenetViewerToContainer(document.querySelector(".doenetml-applet"))`
  — `querySelector`, not `querySelectorAll`, so only the first applet on a
  page can render. Multiple doenet exercises per page will be common; fix to
  iterate (and skip containers marked for on-demand activation). New/changed
  JS belongs in core `js/` (edit `../pretext`, not the CLI's `core.zip`).

### 4.6 New `pretext/lib/doenet.py` (modeled on `lib/stack.py`)

```python
def doenet_extraction(xml_source, pub_file, stringparams, xmlid_root, dest_dir):
    # 1. xsltproc extract-doenet.xsl -> ephemeral XML of (assembly-id, text)
    # 2. lazy import doenetml_to_pretext (common.__module_warning pattern,
    #    like stack.py's "requests"/"fitz" imports); catch the byonm error
    #    string and re-raise with a hint about stray package.json files
    # 3. convert_multiple_doenetml_to_pretext([...])  # one Deno launch
    # 4. per question: parse fragment with lxml, normalize per section 3.1
    # 5. write dest_dir/{assembly-id}.ptx
```

Wire-up: re-export in `pretext/lib/pretext.py`
(`doenet_extraction = doenet.doenet_extraction`, next to the stack
re-export ~line 5689); add a `doenet` component to the `pretext/pretext`
script (`component_info` list ~line 369, `component_dirs` map ~line 133,
dispatch ~line 763); add `doenetml-to-pretext` to `pretext/requirements.txt`
as an optional note (core keeps hard deps minimal — lazy import is the
policy, see stack.py).

### 4.7 Samples & docs

- `examples/sample-book/rune.xml`: replace (or accompany) the experimental
  hand-authored dual exercise with the `<doenet>` form; add
  `examples/sample-book/problems/average-velocity.doenet`.
- `examples/sample-article`: one `<doenet>` exercise including a `<graph>`
  so the PreFigure chain is exercised by CI/manual builds.
- Guide (`doc/guide/`): author-facing section on `<doenet>`; publisher
  section for the activate switch.

## 5. CLI changes (`pretext-cli`)

### 5.1 `pretext/constants.py`

- `ASSET_TO_XPATH["doenet"] = ".//doenet"` (add `[text()]` guard? webwork
  uses `.//webwork[*|@*|text()]`; for doenet bare `.//doenet` is fine since
  an empty element is an authoring error worth surfacing).
- `ASSET_TO_DIR["doenet"] = ["doenet"]`.
- Add `"doenet"` to every format list in `ASSETS_BY_FORMAT` (static formats
  need it for melding; html/runestone need it for the dual static half and
  the on-demand mode; harmless when unused).

### 5.2 `pretext/project/__init__.py`

- `generate_assets()`: add the `core.doenet_extraction(...)` call with
  `dest_dir=self.generated_dir_abspath() / "doenet"`. **Ordering matters**:
  place it with webwork/myopenmath *before* `dynamic-subs` and long before
  `prefigure`/`latex-image` — the image-extraction stylesheets run assembly
  with the default `$exercise-style = 'static'`
  (`pretext-assembly.xsl:229`), so they meld doenet static reps and will
  pick up embedded PreFigure sources only if the reps files already exist.
- `ensure_doenet_reps()` mirroring `ensure_webwork_reps()` (~line 640):
  xpath `.//doenet`, check `generated/doenet/{assembly-id}.ptx` per parent
  exercise, generate on demand; call it beside `ensure_webwork_reps()` in
  `build()` and at the top of `generate_assets()`.
- Failure handling: like webwork — log an error but keep building (HTML is
  fully usable without reps).

### 5.3 `pyproject.toml`

- `[project.optional-dependencies]`: `doenet = ["doenetml-to-pretext>=0.7,<0.8", "deno>=2,<3"]`
  (pin ranges after testing; the `deno` pip package supplies the binary),
  and fold into `all`. Follows the existing `prefigure` extra precedent.
- Friendly runtime error in `generate` when the extra isn't installed:
  "run `pip install pretext[doenet]`".

### 5.4 Tests

- Unit: `doenet_extraction` against 3–4 fixture `.doenet` files (bare
  fragment, `<problem>` with solution, graph → prefigure, converter error),
  with the converter mocked for CI speed plus one real-Deno smoke test
  marked slow/optional.
- Integration (pretext-testing repo has precedent): a tiny project with two
  doenet exercises (one graph); assert (a) HTML contains two live applet
  divs, (b) `pretext build pdf` succeeds with the melded static statement
  and a compiled PreFigure image, (c) build without generation still
  produces working HTML.

## 6. PreFigure end-to-end (v1 commitment — the risky part)

Chain to verify: doenet reps exist → `pretext generate prefigure` runs
`extract-prefigure.xsl` → its assembly (default static style) melds
`doenet-reps/static` → melded `<image><pf:prefigure label="{qid}-…">` is
extracted and compiled → PDF conversion's assembly melds the same rep and
resolves the same generated filename.

Known wrinkles to resolve during implementation:

1. **Filename determinism.** Extraction names outputs via
   `mode="image-source-basename"` which leans on ids stamped in assembly
   pass 6 — but melded content enters at pass 8 and has no `@assembly-id`.
   Check what `image-source-basename` falls back to; the safe fix is to have
   `doenet.py` stamp the rewritten `label`/`xml:id` (`{assembly-id}-…`) and
   ensure the basename derives from that authored-looking id identically in
   both the extraction and conversion runs. This must be proven with a
   2-question, 2-graph test before v1 ships.
2. **prefig dependency**: a doenet graph question silently adds the
   `prefigure` toolchain requirement to PDF builds; the CLI should say so
   (`pip install pretext[prefigure]`) when compilation is attempted without
   it.
3. If determinism turns out to be unachievable at pass 8, fallback design:
   `doenet.py` compiles the PreFigure sources itself at generation time
   (core already has `prefigure_conversion`) into `generated/doenet/images/`
   and rewrites the static rep to `<image pi:generated="doenet/images/…"/>`
   — exactly how STACK handles its server-plotted images
   (`stack.py::_stack_download_assets`). More code, zero ordering risk.
   Decide after wrinkle 1 is investigated.

## 7. Phasing

- **Phase 0 — spike (small, do first)**: run `convert_multiple` over a real
  batch of course questions (e.g. Active Calculus doenet exercises); file
  the upstream issues from section 2 (solution loss, id collisions, byonm,
  seed control request); investigate PreFigure filename determinism
  (section 6.1) since it picks between two designs.
- **Phase 1 — core pipeline**: schema, `extract-doenet.xsl`,
  `lib/doenet.py`, `-c doenet` script component, assembly static meld +
  dynamic synthesis, samples. Milestone: `pretext/pretext -c doenet` +
  a LaTeX build of the sample shows melded statements; HTML shows live
  applets (and fixes the multi-applet querySelector bug).
- **Phase 2 — CLI**: asset type, ordering, `ensure_doenet_reps`, extras,
  tests, CHANGELOG. Milestone: `pretext build pdf` on a doenet project
  "just works" including a graph question (PreFigure e2e).
- **Phase 3 — hosts & polish**: Runestone dual synthesis, activate-button
  mode + publisher variables + JS, guide documentation.

## 8. Deliberately out of scope (v1)

- `<doenet @source="…">` file-reference flavor (webwork-server analogue).
- Seed/variant control (blocked on converter support).
- Standalone (non-exercise) `<doenet>` blocks.
- Braille-specific tuning of converter output beyond what static melding
  gives for free.
- `<task>`-structured doenet exercises (webwork supports task trees; doenet
  questions are monolithic for now).
