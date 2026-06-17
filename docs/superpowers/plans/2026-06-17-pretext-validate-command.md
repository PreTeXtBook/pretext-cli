# `pretext validate` Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `pretext validate [TARGET] [--dev]` command that validates a target's assembled source against the PreTeXt RelaxNG schema and exits non-zero when the document is invalid.

**Architecture:** Refactor schema validation in `pretext/utils.py` into composable engine helpers (`_validate_with_lxml`, existing `_validate_with_jing`) behind an orchestrator `run_schema_validation(etree, schema_file, order)`. The existing build-time `xml_validates_against_schema` becomes a thin wrapper (lxml-first, warn-only, unchanged behavior). A new Click command in `pretext/cli.py` calls the orchestrator jing-first, prints errors, and sets the process exit code.

**Tech Stack:** Python, Click, lxml, pytest, pytest-console-scripts (`script_runner`).

## Global Constraints

- Do **not** change build-time validation behavior or ordering: `xml_validates_against_schema` stays lxml-first and warn-only.
- The three existing validation tests in `tests/test_utils.py` (`test_xml_validates_against_schema_jing_fallback_success`, `..._invalid`, `..._jing_unavailable`) must continue to pass unchanged.
- Engine functions are resolved by bare name inside `run_schema_validation` (call-time module-global lookup) so `monkeypatch.setattr(utils, "_validate_with_jing", ...)` works.
- Exit codes: valid → `0`; invalid → `1`; could-not-validate → `2`. Failure is signaled with `ctx.exit(...)` (raises `SystemExit`, which bypasses `nice_errors`' `except Exception`).
- Schemas live at `resources.resource_base_path() / "core" / "schema" / {pretext.rng | pretext-dev.rng}`.
- `pretext/utils.py` already imports: `from lxml import etree as ET`, `from lxml.etree import _Element`, `from typing import Optional`, `import typing as t`, `from . import ... resources`, and defines `log`.
- `pretext/cli.py` already imports: `utils`, `resources`, `click`, `sys`, `Optional`, `Path`, and defines `log`, `nice_errors`, `CONTEXT_SETTINGS`, `main`.

---

### Task 1: Add lxml engine, orchestrator, and schema-path helpers in `utils.py`

**Files:**
- Modify: `pretext/utils.py` (add helpers near the existing `_validate_with_jing`, which ends around line 294)
- Test: `tests/test_utils.py`

**Interfaces:**
- Consumes: existing `_validate_with_jing(etree: _Element, schema_file: Path) -> Optional[tuple[bool, str]]` (returns `None` when jing is unavailable, `(True, "")` when valid, `(False, error_text)` when invalid).
- Produces:
  - `_validate_with_lxml(etree: _Element, schema_file: Path) -> Optional[tuple[bool, str]]` — `None` when lxml cannot compile the schema (`RelaxNGParseError`), else `(is_valid, error_text)`.
  - `run_schema_validation(etree: _Element, schema_file: Path, order: t.Sequence[str] = ("lxml", "jing")) -> tuple[Optional[bool], str]` — tries each named engine in `order`; returns the first engine result that is not `None`; returns `(None, <reason>)` if every engine is unavailable.
  - `schema_path(dev: bool = False) -> Path` — returns the stable or dev schema file path.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_utils.py` (the file already imports `from lxml import etree as ET` and `from pretext import utils` on this branch):

```python
def test_validate_with_lxml_valid_and_invalid(tmp_path: Path) -> None:
    schema_file = tmp_path / "mini.rng"
    schema_file.write_text(
        '<grammar xmlns="http://relaxng.org/ns/structure/1.0">'
        "<start><element name=\"pretext\"><empty/></element></start></grammar>"
    )

    ok = utils._validate_with_lxml(ET.fromstring("<pretext/>"), schema_file)
    assert ok == (True, "")

    bad = utils._validate_with_lxml(ET.fromstring("<nope/>"), schema_file)
    assert bad is not None
    assert bad[0] is False
    assert bad[1] != ""


def test_validate_with_lxml_uncompilable_schema_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _raise(*args: object, **kwargs: object) -> object:
        raise ET.RelaxNGParseError("boom")

    monkeypatch.setattr(utils.ET, "RelaxNG", _raise)
    assert utils._validate_with_lxml(ET.fromstring("<pretext/>"), tmp_path / "x.rng") is None


def test_run_schema_validation_uses_first_available_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(utils, "_validate_with_jing", lambda *a: (True, ""))
    monkeypatch.setattr(utils, "_validate_with_lxml", lambda *a: (False, "lxml says no"))

    # jing first wins
    assert utils.run_schema_validation(
        ET.fromstring("<pretext/>"), tmp_path / "s.rng", order=("jing", "lxml")
    ) == (True, "")
    # lxml first wins
    assert utils.run_schema_validation(
        ET.fromstring("<pretext/>"), tmp_path / "s.rng", order=("lxml", "jing")
    ) == (False, "lxml says no")


def test_run_schema_validation_skips_unavailable_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(utils, "_validate_with_jing", lambda *a: None)
    monkeypatch.setattr(utils, "_validate_with_lxml", lambda *a: (True, ""))
    assert utils.run_schema_validation(
        ET.fromstring("<pretext/>"), tmp_path / "s.rng", order=("jing", "lxml")
    ) == (True, "")


def test_run_schema_validation_all_unavailable_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(utils, "_validate_with_jing", lambda *a: None)
    monkeypatch.setattr(utils, "_validate_with_lxml", lambda *a: None)
    result = utils.run_schema_validation(
        ET.fromstring("<pretext/>"), tmp_path / "s.rng", order=("jing", "lxml")
    )
    assert result[0] is None
    assert "could not be completed" in result[1]


def test_schema_path_selects_stable_or_dev() -> None:
    assert utils.schema_path(dev=False).name == "pretext.rng"
    assert utils.schema_path(dev=True).name == "pretext-dev.rng"
    assert utils.schema_path().name == "pretext.rng"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_utils.py -k "validate_with_lxml or run_schema_validation or schema_path" -v`
Expected: FAIL with `AttributeError: module 'pretext.utils' has no attribute '_validate_with_lxml'` (and similar for the other new names).

- [ ] **Step 3: Implement the helpers**

In `pretext/utils.py`, immediately after the existing `_validate_with_jing` function (it ends near line 294, just before the `# boilerplate to prevent overzealous caching` comment), add:

```python
def _validate_with_lxml(
    etree: _Element, schema_file: Path
) -> Optional[tuple[bool, str]]:
    # Returns None when lxml cannot compile the schema (the known
    # "no define for ref" bug on some libxml2 builds), so the caller can
    # fall back to another engine.
    try:
        relaxng = ET.RelaxNG(file=str(schema_file))
    except ET.RelaxNGParseError:
        log.debug(
            "lxml could not compile the RelaxNG schema; trying the next validator."
        )
        return None
    try:
        relaxng.assertValid(etree)
        return True, ""
    except ET.DocumentInvalid as err:
        return False, str(err.error_log)


def run_schema_validation(
    etree: _Element,
    schema_file: Path,
    order: t.Sequence[str] = ("lxml", "jing"),
) -> tuple[Optional[bool], str]:
    # Engines are looked up by name here (not captured at import time) so tests
    # can monkeypatch `utils._validate_with_jing` / `utils._validate_with_lxml`.
    engines = {
        "lxml": _validate_with_lxml,
        "jing": _validate_with_jing,
    }
    for engine_name in order:
        result = engines[engine_name](etree, schema_file)
        if result is not None:
            return result
    return None, (
        "Schema validation could not be completed: no validator was available "
        "(jing is not installed and lxml could not compile the schema)."
    )


def schema_path(dev: bool = False) -> Path:
    schema_name = "pretext-dev.rng" if dev else "pretext.rng"
    return resources.resource_base_path() / "core" / "schema" / schema_name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_utils.py -k "validate_with_lxml or run_schema_validation or schema_path" -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add pretext/utils.py tests/test_utils.py
git commit -m "Add lxml engine, orchestrator, and schema-path helpers for validation"
```

---

### Task 2: Refactor `xml_validates_against_schema` to use the orchestrator

**Files:**
- Modify: `pretext/utils.py:210-263` (the `xml_validates_against_schema` function body)
- Test: `tests/test_utils.py` (existing three tests are the safety net — no new tests)

**Interfaces:**
- Consumes: `run_schema_validation(...)`, `schema_path(...)` from Task 1.
- Produces: `xml_validates_against_schema(etree: _Element) -> bool` — same signature and observable build-time behavior as before (lxml-first, warn-only, writes `.error_schema.log` on failure).

- [ ] **Step 1: Confirm the existing tests currently pass (baseline)**

Run: `python -m pytest tests/test_utils.py -k "xml_validates_against_schema" -v`
Expected: PASS (3 tests). This is the refactor safety net.

- [ ] **Step 2: Replace the function body**

In `pretext/utils.py`, replace the entire existing `xml_validates_against_schema` function (from `def xml_validates_against_schema(etree: _Element) -> bool:` through its final `return True`, currently lines ~210-263) with:

```python
def xml_validates_against_schema(etree: _Element) -> bool:
    schemarngfile = schema_path()
    log.debug(f"Validating PreTeXt source against schema {schemarngfile}")
    # Build-time validation stays lxml-first (fast) and warn-only.
    is_valid, error_text = run_schema_validation(
        etree, schemarngfile, order=("lxml", "jing")
    )
    if is_valid:
        log.info("PreTeXt source passed schema validation.")
        return True
    if is_valid is None:
        log.warning(error_text + " Continuing with build.")
    else:
        log.debug(
            "PreTeXt document did not pass schema validation; unexpected output "
            "may result. See .error_schema.log for hints. Continuing with build."
        )
    with open(".error_schema.log", "w") as error_log_file:
        error_log_file.write(error_text)
    return False
```

- [ ] **Step 3: Run the existing validation tests to verify they still pass**

Run: `python -m pytest tests/test_utils.py -k "xml_validates_against_schema" -v`
Expected: PASS (3 tests) — `..._jing_fallback_success` (returns True, no log file), `..._jing_fallback_invalid` (log contains "schema validation error via jing"), `..._jing_unavailable` (log file exists).

- [ ] **Step 4: Run the full utils test module**

Run: `python -m pytest tests/test_utils.py -v`
Expected: PASS (all, including the 6 from Task 1).

- [ ] **Step 5: Commit**

```bash
git add pretext/utils.py
git commit -m "Refactor build-time schema validation to use shared orchestrator"
```

---

### Task 3: Add the `pretext validate` CLI command

**Files:**
- Modify: `pretext/cli.py` (add a new command after the `build` command, which ends near line 730)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `utils.run_schema_validation(...)`, `utils.schema_path(...)` from Task 1; `ctx.obj["project"]` (set in `main`); `project.get_target(name)`; `target.source_element()` (assembles source, returns `_Element`).
- Produces: a Click command `validate` registered on `main`, invokable as `pretext validate [TARGET] [--dev]`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py` (it already imports `Path`, `script_runner: ScriptRunner`, `PTX_CMD`). Add `from lxml import etree as ET` and `from pretext import utils` to its imports, then append:

```python
def _validator_available() -> bool:
    # True if either lxml or jing can run against the bundled schema.
    result = utils.run_schema_validation(
        ET.fromstring("<pretext/>"), utils.schema_path(), order=("lxml", "jing")
    )
    return result[0] is not None


def _make_project(tmp_path: Path, script_runner: ScriptRunner) -> Path:
    assert script_runner.run([PTX_CMD, "new"], cwd=tmp_path).success
    return tmp_path / "new-pretext-project"


def test_validate_invalid_source_is_nonzero(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    project = _make_project(tmp_path, script_runner)
    main_src = project / "source" / "main.ptx"
    main_src.write_text('<?xml version="1.0"?>\n<pretext><bogus-element/></pretext>\n')
    ret = script_runner.run([PTX_CMD, "validate"], cwd=project)
    assert ret.returncode != 0


def test_validate_malformed_xml_is_nonzero(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    project = _make_project(tmp_path, script_runner)
    main_src = project / "source" / "main.ptx"
    main_src.write_text("<pretext>\n")  # not well-formed
    ret = script_runner.run([PTX_CMD, "validate"], cwd=project)
    assert ret.returncode != 0


@pytest.mark.skipif(
    not _validator_available(), reason="no RelaxNG validator (lxml/jing) available"
)
def test_validate_valid_project_is_zero(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    project = _make_project(tmp_path, script_runner)
    ret = script_runner.run([PTX_CMD, "validate"], cwd=project)
    assert ret.returncode == 0


@pytest.mark.skipif(
    not _validator_available(), reason="no RelaxNG validator (lxml/jing) available"
)
def test_validate_dev_schema_runs(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    project = _make_project(tmp_path, script_runner)
    ret = script_runner.run([PTX_CMD, "validate", "--dev"], cwd=project)
    assert ret.returncode == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -k "validate" -v`
Expected: FAIL — `pretext validate` is not yet a command, so the runs exit non-zero with a "No such command 'validate'" usage error. (The two `..._nonzero` tests may *accidentally* pass for the wrong reason; that is fine — they will pass for the right reason after Step 3. The `..._is_zero` test will FAIL, proving the command is missing.)

- [ ] **Step 3: Implement the command**

In `pretext/cli.py`, add the following after the `build` command function (after its body ends near line 730, before the `@main.command(...)` for `generate`):

```python
@main.command(
    short_help="Validate source against the PreTeXt schema",
    context_settings=CONTEXT_SETTINGS,
)
@click.argument("target_name", required=False, metavar="target")
@click.option(
    "--dev",
    is_flag=True,
    help="Validate against the development schema (pretext-dev.rng) instead of the "
    "stable schema, allowing experimental elements.",
)
@click.pass_context
@nice_errors
def validate(ctx: click.Context, target_name: Optional[str], dev: bool) -> None:
    """
    Validate the source of TARGET against the PreTeXt RelaxNG schema.

    Reports schema errors and exits with a non-zero status when the document is
    invalid, so it can gate CI or pre-commit checks. Without TARGET, the first
    target in project.ptx is used. Exit codes: 0 = valid, 1 = invalid, 2 =
    validation could not be performed (no validator available).
    """
    project = ctx.obj["project"]
    target = project.get_target(target_name)

    # Assemble the source (resolves xinclude); surfaces syntax/xinclude errors.
    try:
        etree = target.source_element()
    except Exception as e:
        log.error(f"Could not assemble source for validation: {e}")
        ctx.exit(1)

    schema_file = utils.schema_path(dev)
    log.info(f"Validating source against schema {schema_file.name}.")
    is_valid, error_text = utils.run_schema_validation(
        etree, schema_file, order=("jing", "lxml")
    )

    if is_valid:
        log.info(f"PreTeXt source passed schema validation ({schema_file.name}).")
        return
    if is_valid is None:
        log.error(error_text)
        ctx.exit(2)

    with open(".error_schema.log", "w") as error_log_file:
        error_log_file.write(error_text)
    log.error("PreTeXt source did NOT pass schema validation:")
    log.error(error_text)
    log.error("See .error_schema.log for the full report.")
    ctx.exit(1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -k "validate" -v`
Expected: PASS (the two `..._nonzero` tests pass; the two skipif tests pass when a validator is available, else skip).

- [ ] **Step 5: Confirm the command is wired up**

Run: `pretext validate -h`
Expected: Help text for the validate command, showing the `--dev` option and the `[target]` argument.

- [ ] **Step 6: Commit**

```bash
git add pretext/cli.py tests/test_cli.py
git commit -m "Add pretext validate command"
```

---

### Task 4: Document the command in the changelog

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:** none.

- [ ] **Step 1: Add a changelog entry**

Open `CHANGELOG.md`, find the top-most "unreleased"/in-progress section (matching the existing format used by recent entries), and add a bullet:

```markdown
- Added a `pretext validate` command that checks a target's source against the
  RelaxNG schema and exits non-zero on failure (use `--dev` for the development
  schema). Tries `jing` first, then falls back to lxml's built-in validator.
```

- [ ] **Step 2: Verify the changelog format matches surrounding entries**

Run: `git diff CHANGELOG.md`
Expected: a single added bullet under the current unreleased section, consistent indentation/style with neighbors.

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "Document pretext validate command in changelog"
```

---

## Self-Review

**1. Spec coverage:**
- Command surface `pretext validate [TARGET]`, single-target default, assembled source → Task 3. ✓
- `--dev` flag selecting `pretext-dev.rng` → `schema_path` (Task 1) + flag wiring (Task 3) + test (Task 3). ✓
- Engine jing-first/lxml-backup → Task 3 calls orchestrator `order=("jing","lxml")`. ✓
- Exit codes 0/1/2 + `ctx.exit` to bypass `nice_errors` → Task 3 + Global Constraints. ✓
- `.error_schema.log` written on invalid → Task 3. ✓
- utils refactor (shared engines, unchanged build path) → Tasks 1 & 2. ✓
- Build stays lxml-first/warn-only/unchanged → Task 2 + Global Constraints, guarded by existing tests. ✓
- Testing: orchestrator unit tests (Task 1), build-path regression (Task 2), CLI exit-code/`--dev` tests (Task 3). ✓
- Phase-2 wasm direction → documented in spec; intentionally out of scope of this plan. ✓

**2. Placeholder scan:** No TBD/TODO/"add error handling"/"similar to" — every code and test step contains complete content. ✓

**3. Type consistency:** `_validate_with_lxml`, `_validate_with_jing`, and the orchestrator all share `(_Element, Path) -> Optional[tuple[bool, str]]`; orchestrator returns `tuple[Optional[bool], str]`; `schema_path(dev: bool) -> Path`; command consumes these exact names. Build wrapper keeps `(_Element) -> bool`. Consistent across tasks. ✓
