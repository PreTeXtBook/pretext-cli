# Working on the PreTeXt CLI

The CLI wraps PreTeXt core (the `pretext` repository): `pretext/core/` holds core's Python library, and the stylesheets, schema, CSS, and JavaScript are installed under `~/.ptx/<version>/core`. Setup is in the Development section of [README.md](README.md).

## Commands

- Install and fetch the pinned core: `uv sync --all-extras`, then `uv run python scripts/fetch_core.py`. Rerun the fetch whenever `CORE_COMMIT` in `pretext/__init__.py` changes upstream.
- Run the development CLI with `uv run pretext ...`, never a bare `pretext`, which may be a separately installed release.
- Before committing: `uv run black .`, `uv run flake8`, `uv run mypy`, and `uv run pytest` (narrow with `-k <name>`).
- Add user-facing changes to [CHANGELOG.md](CHANGELOG.md) under `## [Unreleased]`; the release workflow adds version headings.

## Developing alongside core

Many changes span both repositories. [docs/core_development.md](docs/core_development.md) describes linking a core checkout into the CLI with `scripts/symlink_core.py` and undoing it with `scripts/unlink_core.py`.

- Check whether core is linked before reasoning about which core code runs:

      uv run python -c "from pathlib import Path; print(Path('pretext/core/pretext.py').is_symlink())"

  `True` means the CLI runs the core checkout (by default `../pretext`) for both Python and the stylesheets. `False` means it runs the frozen copy pinned by `CORE_COMMIT`, and core edits have no effect on CLI builds.
- Core's `AGENTS.md` says to test with its `pretext/pretext` script rather than the CLI, because an installed CLI bundles a frozen copy of core. When core is linked, that premise does not hold: `uv run pretext build` exercises the checkout, and both routes are valid tests. Use the CLI route when the change involves CLI behavior (project manifests, targets, `generate`, `view`); use `pretext/pretext` for a core-only check.
- Edits inside the core checkout follow core's rules. Read `../pretext/AGENTS.md` and the `AGENTS.md` nearest the files being changed, and commit there in core's style (`Area: lowercase description`, no body). Those rules do not apply to commits in this repository.
- Core treats the public function signatures in `pretext/lib/pretext.py` as an interface: a new parameter is required and positional, with no default. When a core change adds one, update the callers here (`pretext/project/__init__.py`, `pretext/project/generate.py`, `pretext/utils.py`) in the same piece of work.
- A CLI change that depends on unreleased core work cannot ship until `CORE_COMMIT` is bumped to a core commit that contains it. Say so in the pull request.
- Unlink with `uv run python scripts/unlink_core.py` before testing against the pinned core.

## Windows

- Linking core creates symbolic links, which Windows permits only with Developer Mode enabled (Settings → System → For developers) or from an elevated shell.
- Activate the virtual environment with `.venv\Scripts\activate`, or use `uv run` and skip activation.
