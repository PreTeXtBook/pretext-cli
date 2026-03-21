# Copilot Instructions for pretext-cli

Prefer running project commands with `poetry run` so they use the repository's
configured Python environment and tool versions.

When working on an assigned GitHub issue and preparing to open a pull request,
run code formatting before creating the PR:

```bash
poetry run black .
```

Only open the PR after formatting has been run successfully.

When changes affect behavior in `pretext/`, add or update tests in `tests/`
that cover the change.

Prefer test-driven development whenever practical: write or update tests first,
then implement the code change to satisfy them.

Before opening the PR, run relevant tests (or the full suite when needed):

```bash
poetry run pytest
```

For user-visible changes, add an entry under `[Unreleased]` in `CHANGELOG.md`
using Keep a Changelog categories (Added, Changed, Fixed, Removed).
