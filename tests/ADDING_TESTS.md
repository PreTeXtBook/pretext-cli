# Adding tests for new features

When you add a feature to pretext-cli, the test goes in one of these files:

| You added… | Test goes in… | Why |
|---|---|---|
| A CLI command or flag | `test_cli.py` | Exercises the `pretext` script end-to-end; asserts exit codes and files on disk |
| A change to `pretext.project.Project` or `pretext.project.Target` | `test_project.py` | Tests the library API directly; faster than CLI, easier to inspect state |
| A pure helper in `pretext.utils` | `test_utils.py` | Unit tests for string/path/version logic |
| Registry/server bookkeeping in `pretext.server` | `test_server.py` | Monkeypatch `home_path` so the real `~/.ptx` is never touched |
| Asset generation (individual_* wrappers) | `test_generate.py` | Mock the core conversion; assert the wrapper raises on missing output |

## General patterns

**Start with a module docstring** describing what you're testing:

```python
"""
Unit tests for `pretext.mymodule`.

Focus: what the module does and which tests cover the key paths.
"""
```

**Every test needs a docstring** that states the behavior, not just the test name:

```python
def test_build_with_custom_xsl(tmp_path: Path) -> None:
    """A target with custom XSL copies all XSL files to the output directory
    and builds using the custom stylesheet."""
    # implementation
```

**Use fixtures from `conftest.py` or define your own:**

```python
@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Copy the simple project into tmp_path and return its root."""
    prj = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj)
    return prj
```

**For CLI tests:** use the `script_runner` fixture (from pytest-console-scripts):

```python
def test_new_with_custom_template(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """pretext new TEMPLATE produces the expected source structure."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "article", "-d", "."],
        cwd=tmp_path
    ).success
    assert (tmp_path / "source").is_dir()
```

**For library tests:** call the Python API directly:

```python
def test_project_parses_manifest(tmp_path: Path) -> None:
    """Project.parse() reads the manifest and populates targets."""
    shutil.copytree(EXAMPLES_DIR / "projects" / "simple", tmp_path / "proj")
    with utils.working_directory(tmp_path / "proj"):
        project = pr.Project.parse()
        assert project.get_target("web") is not None
```

**Skip tests that need external executables:**

```python
@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found.",
)
def test_pdf_build(tmp_path: Path) -> None:
    """A pdf target builds a .pdf file."""
    # implementation
```

**Group related assertions** so the test's intent is clear:

```python
def test_deployment_strategy(tmp_path: Path) -> None:
    """The deploy strategy changes as the project configuration evolves."""
    project = pr.Project(ptx_version="2")
    
    # One target → default_target strategy
    project.new_target("web", "html")
    assert project.deploy_strategy() == "default_target"
    
    # Mark one for deployment → pelican_default strategy
    project.get_target("web").deploy = "yes"
    assert project.deploy_strategy() == "pelican_default"
```

## Running your tests

```bash
# Run all tests
pytest

# Run one file
pytest tests/test_cli.py

# Run one test
pytest tests/test_cli.py::test_build_with_custom_xsl

# Run with verbose output and stop on first failure
pytest -vvx

# Run in parallel (if pytest-xdist is installed)
pytest -n auto
```

## Before you push

```bash
# Format code
black tests/ pretext/

# Check lint
flake8 tests/ pretext/

# Check types
mypy --install-types --non-interactive
```

CI will fail if any of these fail locally, so catch it early.

## Fixtures and helpers

Use `tmp_path` (pytest built-in) for temporary directories — never write to `/tmp` directly.

The `EXAMPLES_DIR` constant points to `tests/examples/projects/`. Copy fixture projects into `tmp_path`:

```python
project = tmp_path / "my_project"
shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", project)
```

Never build inside `tests/examples/` — always copy to a temp location first.

The `utils.working_directory(path)` context manager temporarily changes the working directory:

```python
with utils.working_directory(project):
    p = pr.Project.parse()  # looks for project.ptx in cwd
```

## Known limitations

Tests that require a real GitHub remote (e.g., `pretext deploy` pushing to gh-pages) are not exercised. The staging logic is covered; only the `ghp-import` push is skipped.

Tests for external services (downloading templates with `--url-template`, running `pretext upgrade` via pip) are not included — these would be integration tests in a separate CI step.
