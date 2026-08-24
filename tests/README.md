# PreTeXt-CLI test suite

**New to writing tests?** Start with [ADDING_TESTS.md](ADDING_TESTS.md) — a guide to choosing which test file, common patterns, and how to run them.

Run the suite from the repository root with:

```bash
uv run pytest          # or: pytest -n auto if you install pytest-xdist
```

Tests that need external executables (`xelatex`, `asy`, `sage`) skip
themselves when those aren't installed, so a partial toolchain still gives a
meaningful (if smaller) run. CI runs the full suite in the
`pretextbook/pretext-full` container (see `.github/workflows/tests.yml`).

## Layout

| File | Level | What it covers |
| --- | --- | --- |
| `test_cli.py` | end-to-end | The `pretext` command surface, one section per command group: basics (`--version`, `devscript`, `support`), scaffolding (`new`, `init`, `update-project`), `build` and its flags, `generate` and asset regeneration rules, `validate` exit codes, `view` server lifecycle, `deploy --stage-only`, `import`. |
| `test_project.py` | library | The `pretext.project` API: manifest parsing (v2 + legacy), target defaults and validation, builds per format (html, pdf, latex, epub, runestone, zip), subset builds, asset tables, deploy/staging strategies. |
| `test_sample_article.py` | full stack | Builds core PreTeXt's sample article with zero logged errors. The heaviest single test; needs xelatex + asy + sage. |
| `test_generate.py` | unit (mocked) | The `individual_*` asset-generation wrappers raise when core fails to produce an output file, so failures are never cached as successes. |
| `test_utils.py` | unit | Pure helpers in `pretext.utils`: project discovery, version comparison, schema-validation engine selection, resource-modification detection, misc string/path utilities. |
| `test_server.py` | unit | The `~/.ptx/running_servers` registry behind `pretext view`: entry serialization, lookup, purge of dead entries. Uses a temp home dir and fake pids only. |
| `common.py` | — | Shared helpers: `EXAMPLES_DIR`, `check_installed`. |
| `examples/projects/` | fixtures | Small projects copied into `tmp_path` by tests. `project_refactor/simple` (minimal v2 manifest), `project_refactor/elaborate` (every manifest attribute customized), `project_refactor/legacy*` (v1 manifests), plus one-feature projects (`latex-image`, `prefigure`, `graphics`, `datafile`, `interactive`, `custom-xsl`, `custom-wwserver`, `xref`, `xi_pub`). |

Conventions:

- Every test copies its fixture project into `tmp_path` before building;
  never build inside `tests/examples`.
- CLI behavior is asserted through the real `pretext` script via the
  `script_runner` fixture (exit codes + files on disk), not by calling
  command functions directly.
- Anything touching the real home directory (the server registry) must
  monkeypatch `server.home_path`.

## Known gaps / intentionally untested

- `pretext deploy` beyond `--stage-only`: a real deploy needs a GitHub
  remote and pushes a `gh-pages` branch. The staging logic is covered
  (`test_project.py::test_stage`); the `ghp-import` push is not.
- `pretext upgrade` (runs pip against the environment) and
  `pretext new --url-template` (downloads a zip from the network).
- kindle, braille, and webwork output formats (need kindlegen/liblouis or
  network services).
- The full demo-template build (`test_cli.py::test_build`) is currently
  skipped: a subset build fails before a full build has generated the qrcode
  xml files, and the full build is expensive. The pieces are covered
  separately (subset builds, qrcode/preview generation).
- `pretext view`'s browser launching and codespace-specific server path.
