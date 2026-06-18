# Design: `pretext validate` command

**Date:** 2026-06-17
**Status:** Approved (pending spec review)
**Branch:** `validate`

## Summary

Add a standalone `pretext validate` command that checks a target's assembled
PreTeXt source against the RelaxNG schema, reports errors clearly, and **exits
non-zero on failure** so it can gate CI and pre-commit workflows.

This is distinct from the existing build-time validation, which only *warns and
continues* (the return value of `utils.xml_validates_against_schema` is ignored
at `project/__init__.py:742`).

## Motivation

- Authors and CI want a way to confirm a document is schema-valid *without*
  running a full build.
- Build-time validation is intentionally lenient (warn-only) and lxml-first for
  speed. A dedicated command can afford to be stricter and more correct.

## Command surface

```
pretext validate [TARGET] [--dev]
```

- New `@main.command` in `pretext/cli.py`, mirroring the `build` command:
  `@click.argument("target_name", required=False)`, `@click.pass_context`,
  `@nice_errors`.
- Resolves the project from `ctx.obj["project"]` and the target via
  `project.get_target(target_name)`.
- **Single-target default**: with no `TARGET`, validates the first target's
  source (consistent with `build`/`generate`/`view`).
- Calls `target.source_element()` to **assemble** the source. This resolves
  XInclude and surfaces XML-syntax/XInclude errors using existing messaging
  before schema validation runs.

### `--dev` flag

- Default: validate against the **stable** schema `core/schema/pretext.rng`.
- `--dev`: validate against the **development** schema
  `core/schema/pretext-dev.rng` (permits experimental elements not yet in the
  stable release). Both files already ship in the bundled core.
- No custom-`--schema`-path flag for now (YAGNI; trivial to add later, since
  schema selection is already a parameter of the engine helpers).

## Validation engine: jing-first, lxml-backup

For the standalone command, try **jing first** (correct on the full schema),
fall back to **lxml's** built-in RelaxNG if jing is not installed.

Build-time validation is **unchanged**: it stays lxml-first and warn-only so it
is not slowed down.

### Outcomes and exit codes

| Outcome | Behavior | Exit code |
|---|---|---|
| Valid | Success message | `0` |
| Invalid | Print errors to terminal (stderr) + write `.error_schema.log` | `1` |
| Could not validate (jing absent **and** lxml hits the "no define for ref" compile bug) | Clear message that validity could not be confirmed | `2` |

A distinct exit code for "could not validate" prevents CI from going silently
green when no engine could actually run.

### Exit-code gotcha

`nice_errors` (`cli.py:40`) catches every `Exception`, logs it, and returns
normally — yielding exit code `0`. To make the non-zero contract work, the
command signals failure with `ctx.exit(1)` / `sys.exit(...)`, which raise
`SystemExit` (a `BaseException`, not `Exception`); these slip past the
`except Exception` and let Click set the process exit code.

## `utils` refactor (shared engine, unchanged build path)

Goal: share engine logic without changing build-time behavior or speed.

- Factor the two engines into peer helpers, each returning `(is_valid, error_text)`
  or `None` (meaning "this engine could not run"):
  - `_validate_with_jing(etree, schema_file)` — already exists.
  - `_validate_with_lxml(etree, schema_file)` — new; returns `None` on
    `RelaxNGParseError` (the compile bug) so the orchestrator can fall back.
- Add an orchestrator:
  `run_schema_validation(etree, schema_file, order) -> tuple[Optional[bool], str]`
  where `order` is the engine sequence to try; result `None` means "could not
  validate with any engine".
- Keep `xml_validates_against_schema(etree)` for the **build path**: a thin
  wrapper that calls the orchestrator with `order=[lxml, jing]`, stays warn-only,
  and returns `bool`. Build behavior and ordering are preserved.
- The new command calls the orchestrator with `order=[jing, lxml]`, resolves the
  schema file from `--dev`, and acts on the `(Optional[bool], error_text)` result
  to print errors and set the exit code.

## Testing

- Unit tests in `tests/test_utils.py` for the orchestrator (extending the
  existing monkeypatch-based tests on this branch):
  - jing-first ordering when both engines are available,
  - fallback to lxml when jing returns `None`,
  - `None` result when both engines are unavailable.
- CLI test: `pretext validate` exits `0` on a known-valid sample and non-zero on
  a known-invalid sample; `--dev` selects the dev schema file.

## Future direction (phase 2, out of scope here)

Replace the Java dependency with a correct, pure-install engine:

- pretext-cli's **release CI** checks out `siefkenj/relaxng_validator_wasm` and
  builds Python wheels via `maturin` for each platform/Python version, then
  vendors or depends on them.
- The orchestrator gains a `wasm` engine that goes to the **front** of `order`
  for the validate command, with jing/lxml remaining as fallbacks.
- Note: building maturin/PyO3 wheels requires a Rust toolchain at *build* time;
  this is a CI/release-pipeline step, not a build-at-runtime step on the user's
  machine. The validator is not yet published to PyPI, which is why phase 1 ships
  on jing + lxml.

## Out of scope

- Schematron / `pretext-validation-plus.xsl` semantic validation.
- Custom arbitrary `--schema PATH` flag.
- Validating all targets at once (single-target default; could be revisited).
- Changing build-time validation behavior.
