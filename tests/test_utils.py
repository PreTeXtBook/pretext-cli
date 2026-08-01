"""
Unit tests for `pretext.utils`.

These cover the pure helper functions of the CLI: project discovery,
version handling, schema validation plumbing, resource-modification
detection, and small string/path utilities.  Anything requiring a real
`pretext build` lives in ``test_project.py`` / ``test_cli.py`` instead.
"""

import fnmatch
import os
import sys
import typing as t
import pytest
from pathlib import Path
from lxml import etree as ET  # noqa: N812
from pretext import utils


def test_working_directory(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    subdir = Path("foobar")
    subdir.mkdir()
    assert Path().resolve() == tmp_path.resolve()
    with utils.working_directory(subdir):
        assert Path().resolve().parent == tmp_path.resolve()
    # After exiting context manager, the directory should have returned to the original
    assert Path().resolve() == tmp_path.resolve()


def test_project_path(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    Path("project.ptx").write_text("")
    assert Path("project.ptx").exists()
    assert utils.project_path_found().resolve() == tmp_path.resolve()
    subdir = Path("foobar")
    print(subdir.resolve())
    subdir.mkdir()
    os.chdir(subdir)
    assert utils.project_path_found().resolve() == Path().resolve().parent


def test_parse_git_remote() -> None:
    valids = [
        "git@github.com:PreTeXtBook/pretext-cli.git",
        "https://github.com/PreTeXtBook/pretext-cli.git",
        "https://github.com/PreTeXtBook/pretext-cli",
        "https://github.com/PreTeXtBook/pretext-cli/",
    ]
    for string in valids:
        assert utils.parse_git_remote(string)[0] == "PreTeXtBook"
        assert utils.parse_git_remote(string)[1] == "pretext-cli"


def test_is_unmodified() -> None:
    """A resource file containing the legacy magic comment is always treated
    as unmodified (i.e. safe for `pretext update` to overwrite)."""
    magic_comment = (
        b"foo\n<!-- Managed automatically by PreTeXt authoring tools -->\nbar"
    )
    assert utils.is_unmodified("foo", magic_comment)


def test_is_unmodified_edited_file_returns_false() -> None:
    """A resource file without the magic comment or a known version header
    is treated as user-modified, so `pretext update` must not overwrite it."""
    assert not utils.is_unmodified("foo", b"user wrote this themselves\n")
    # A version header whose hash doesn't match any known resource hash is
    # also considered modified.
    versioned = b"# File automatically generated with PreTeXt 0.0.1.\nedited\n"
    assert not utils.is_unmodified(".gitignore", versioned)


def test_is_unmodified_requirements_with_version_header() -> None:
    """requirements.txt is special-cased: any version header marks it
    unmodified, since its content is just the pinned pretext version."""
    contents = b"# automatically generated with PreTeXt 2.36.0\npretext == 2.36.0\n"
    assert utils.is_unmodified("requirements.txt", contents)


def test_requirements_version(tmp_path: Path) -> None:
    # Create a minimal project.ptx so project_path() can find the project root
    (tmp_path / "project.ptx").write_text("")

    cases = [
        ("pretext == 2.36.0", "2.36.0"),
        ("pretextbook == 1.2.3", "1.2.3"),
        ("pretext[prefigure] == 2.36.0", "2.36.0"),
        ("  pretext  ==  3.0.0  ", "3.0.0"),
        ("pretext[prefigure,extra] == 0.9.1", "0.9.1"),
    ]

    for line, expected in cases:
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(line + "\n")
        assert utils.requirements_version(tmp_path) == expected, f"Failed for: {line!r}"

    # Lines that should NOT match
    non_matching = [
        "numpy == 1.0.0",
        "pretext ==",
        "pretext",
    ]
    for line in non_matching:
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(line + "\n")
        assert (
            utils.requirements_version(tmp_path) is None
        ), f"Should not match: {line!r}"


def test_format_docstring_as_help_str() -> None:
    # Leading/trailing whitespace on each line is stripped, and single newlines
    # within a paragraph are collapsed to a single space.
    docstring = """
    First line of text
    that continues here.

    Second paragraph.
    """
    result = utils.format_docstring_as_help_str(docstring)
    assert "First line of text that continues here." in result
    assert "Second paragraph." in result
    # Double newlines (paragraph breaks) are preserved as "\n\n".
    assert "\n\n" in result

    # A single-line docstring has no newlines.
    assert "\n" not in utils.format_docstring_as_help_str("Single line.")
    assert utils.format_docstring_as_help_str("  spaced  ") == "spaced"

    # An empty string produces an empty string.
    assert utils.format_docstring_as_help_str("") == ""


def test_is_earlier_version() -> None:
    assert utils.is_earlier_version("1.0.0", "2.0.0")
    assert utils.is_earlier_version("2.0.0", "2.1.0")
    assert utils.is_earlier_version("2.1.0", "2.1.1")
    assert not utils.is_earlier_version("2.0.0", "1.0.0")
    assert not utils.is_earlier_version("2.1.0", "2.0.0")
    assert not utils.is_earlier_version("2.1.1", "2.1.0")
    # Equal versions are not earlier.
    assert not utils.is_earlier_version("1.2.3", "1.2.3")
    # When the primary digits are equal but the strings differ only in length,
    # the shorter version string is treated as earlier. In pretext-cli, dev
    # builds (e.g. "2.11.5.dev0") are nightly POST-release builds produced
    # *after* the stable release, so "2.11.5" is earlier than "2.11.5.dev0".
    assert utils.is_earlier_version("2.11.5", "2.11.5.dev0")
    assert not utils.is_earlier_version("2.11.5.dev0", "2.11.5")


def test_core_modules_included_in_package() -> None:
    if sys.version_info >= (3, 11):
        import tomllib

        opener = lambda p: open(p, "rb")  # noqa: E731
        loader = tomllib.load
    else:
        import toml

        opener = lambda p: open(p, "r")  # noqa: E731
        loader = toml.load

    root = Path(__file__).parent.parent
    with opener(root / "pyproject.toml") as f:
        config = loader(f)

    includes: list[str] = config["tool"]["hatch"]["build"]["artifacts"]

    core_dir = root / "pretext" / "core"
    core_files = [
        str(p.relative_to(root))
        for p in sorted(core_dir.glob("*.py"))
        if p.name != "__init__.py"
    ]

    for rel_path in core_files:
        covered = any(fnmatch.fnmatch(rel_path, pat) for pat in includes)
        assert covered, (
            f"{rel_path} is not covered by any entry in pyproject.toml [tool.hatch.build] artifacts.\n"
            f"Add it explicitly or use a glob like 'pretext/core/*.py'."
        )


def test_hash_path(tmp_path: Path) -> None:
    # hash_path should return a 10-character hex string.
    result = utils.hash_path(tmp_path)
    assert isinstance(result, str)
    assert len(result) == 10
    assert all(c in "0123456789abcdef" for c in result)
    # The same path should always produce the same hash.
    assert utils.hash_path(tmp_path) == utils.hash_path(tmp_path)
    # Different paths should (almost certainly) produce different hashes.
    other_path = tmp_path / "subdir"
    assert utils.hash_path(tmp_path) != utils.hash_path(other_path)


def test_xml_syntax_is_valid(tmp_path: Path) -> None:
    # A well-formed PreTeXt file should pass validation.
    valid_xml = tmp_path / "valid.ptx"
    valid_xml.write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<pretext>\n"
        "  <article xml:id='article-id'>\n"
        "    <title>Hello</title>\n"
        "    <p>Content.</p>\n"
        "  </article>\n"
        "</pretext>\n"
    )
    assert utils.xml_syntax_is_valid(valid_xml)

    # A file whose root tag is not <pretext> should fail.
    wrong_root = tmp_path / "wrong_root.ptx"
    wrong_root.write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<notpretext>\n"
        "  <p>Content.</p>\n"
        "</notpretext>\n"
    )
    assert not utils.xml_syntax_is_valid(wrong_root)

    # A file with malformed XML should fail.
    bad_xml = tmp_path / "bad.ptx"
    bad_xml.write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<pretext>\n"
        "  <unclosed-tag>\n"
        "</pretext>\n"
    )
    assert not utils.xml_syntax_is_valid(bad_xml)

    # A nonexistent file should raise IOError.
    with pytest.raises(IOError):
        utils.xml_syntax_is_valid(tmp_path / "nonexistent.ptx")


def test_jing_command_prefers_configured_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `jing` configured in executables.ptx wins over one on the PATH, and
    keeps its options (jing is a Java program, so it may be a whole command)."""
    configured = ["/opt/java", "-jar", "/opt/jing.jar"]
    monkeypatch.setattr(utils.core, "get_executable_cmd", lambda name: configured)
    monkeypatch.setattr(utils.shutil, "which", lambda name: "/usr/bin/jing")
    assert utils._jing_command() == configured


@pytest.mark.parametrize("error", [KeyError("jing"), TypeError(), OSError("missing")])
def test_jing_command_falls_back_to_path(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """With no usable configured jing -- no `jing` key, no project loaded, or a
    command that isn't installed -- fall back to a jing on the PATH."""

    def _raise(name: str) -> object:
        raise error

    monkeypatch.setattr(utils.core, "get_executable_cmd", _raise)
    monkeypatch.setattr(utils.shutil, "which", lambda name: "/usr/bin/jing")
    assert utils._jing_command() == ["/usr/bin/jing"]


def test_jing_command_none_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(name: str) -> object:
        raise OSError("missing")

    monkeypatch.setattr(utils.core, "get_executable_cmd", _raise)
    monkeypatch.setattr(utils.shutil, "which", lambda name: None)
    assert utils._jing_command() is None
    # And the engine reports itself unavailable, rather than "invalid".
    assert utils.validate_with_jing(Path("source.xml"), Path("s.rng")) is None


def test_validate_with_jing_invokes_configured_command(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The configured command line, options and all, is what gets run."""
    recorded: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd: list[str], **kwargs: object) -> _Result:
        recorded.append(cmd)
        return _Result()

    monkeypatch.setattr(
        utils, "_jing_command", lambda: ["java", "-jar", "/opt/jing.jar"]
    )
    monkeypatch.setattr(utils.subprocess, "run", _run)

    schema_file = tmp_path / "mini.rng"
    source_file = tmp_path / "source.xml"
    assert utils.validate_with_jing(source_file, schema_file) == (True, "")
    assert recorded[0] == [
        "java",
        "-jar",
        "/opt/jing.jar",
        str(schema_file),
        str(source_file),
    ]


@pytest.mark.parametrize(
    "returncode, expected",
    # 0 = valid, 1 = the document has messages, anything more = jing itself
    # failed, which is "nothing was checked" rather than "invalid".
    [(0, (True, "boom")), (1, (False, "boom")), (2, None), (127, None)],
)
def test_validate_with_jing_maps_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncode: int,
    expected: t.Optional[tuple[bool, str]],
) -> None:
    class _Result:
        stdout = "boom"
        stderr = ""

    _Result.returncode = returncode  # type: ignore[attr-defined]

    monkeypatch.setattr(utils, "_jing_command", lambda: ["jing"])
    monkeypatch.setattr(utils.subprocess, "run", lambda *a, **k: _Result())
    assert utils.validate_with_jing(tmp_path / "s.xml", tmp_path / "s.rng") == expected


def test_salve_shim_command_needs_node(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without node there is no salve engine -- and asking for it must not have
    the side effect of installing the CLI's resources."""
    monkeypatch.setattr(utils.shutil, "which", lambda name: None)

    def _no_resources() -> Path:
        raise AssertionError("resource_base_path() should not be reached")

    monkeypatch.setattr(utils.resources, "resource_base_path", _no_resources)
    assert utils.salve_shim_command() is None


def test_salve_shim_command_needs_npm_on_first_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The shim installs itself with npm the first time; without npm, the engine
    is simply unavailable rather than half installed."""
    monkeypatch.setattr(
        utils.shutil, "which", lambda name: "/usr/bin/node" if name == "node" else None
    )
    monkeypatch.setattr(utils.resources, "resource_base_path", lambda: tmp_path)
    assert utils.salve_shim_command() is None
    assert not (tmp_path / "salve" / "node_modules").exists()


def test_salve_shim_command_when_installed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Once installed, the command is `node <shim>` -- the shape core needs for
    an executable it will call with a schema and a source file."""
    shim_dir = tmp_path / "salve"
    (shim_dir / "node_modules").mkdir(parents=True)
    (shim_dir / "ptx-jing-shim.mjs").write_text("// shim")
    monkeypatch.setattr(utils.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(utils.resources, "resource_base_path", lambda: tmp_path)
    assert utils.salve_shim_command() == [
        "/usr/bin/node",
        str(shim_dir / "ptx-jing-shim.mjs"),
    ]


def test_warn_on_schema_errors_writes_log_not_terminal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A build's schema check leaves the messages in a log file, alongside the
    assembled source their line numbers refer to."""
    monkeypatch.setattr(
        utils, "validate_with_jing", lambda source, schema: (False, "line 4: bad")
    )
    assert utils.warn_on_schema_errors(ET.fromstring("<pretext/>"), tmp_path) is False
    assert (tmp_path / "schema-errors.log").read_text() == "line 4: bad"
    assert (tmp_path / "schema-assembled-source.xml").exists()


def test_warn_on_schema_errors_cleans_up_when_valid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A clean run clears the artifacts of an earlier failed one, so no stale
    log is left to be read as the result of this build."""
    (tmp_path / "schema-errors.log").write_text("errors from a previous build")
    monkeypatch.setattr(utils, "validate_with_jing", lambda source, schema: (True, ""))
    assert utils.warn_on_schema_errors(ET.fromstring("<pretext/>"), tmp_path) is True
    assert not (tmp_path / "schema-errors.log").exists()
    assert not (tmp_path / "schema-assembled-source.xml").exists()


def test_warn_on_schema_errors_without_jing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No jing means nothing was checked -- which must not look like success."""
    monkeypatch.setattr(utils, "validate_with_jing", lambda source, schema: None)
    assert utils.warn_on_schema_errors(ET.fromstring("<pretext/>"), tmp_path) is None
    assert not (tmp_path / "schema-errors.log").exists()
    assert not (tmp_path / "schema-assembled-source.xml").exists()


def test_schema_path_selects_stable_or_dev() -> None:
    """schema_path() returns the stable schema by default, or the dev schema
    (which allows experimental elements) when dev=True."""
    assert utils.schema_path(dev=False).name == "pretext.rng"
    assert utils.schema_path(dev=True).name == "pretext-dev.rng"
    assert utils.schema_path().name == "pretext.rng"


def test_clean_asset_table() -> None:
    """clean_asset_table drops asset *types* that disappeared from the source
    (the clean table), keeping the remaining types' cached hashes intact."""
    dirty = {
        "asymptote": {"id1": b"hash1", "id2": b"hash2"},
        "sageplot": {"id3": b"hash3"},
    }
    clean = {"asymptote": {"id1": b"hash1"}}
    result = utils.clean_asset_table(dirty, clean)  # type: ignore[arg-type]
    # sageplot is gone from the source, so it is purged...
    assert "sageplot" not in result
    # ...but surviving asset types keep all their entries.
    assert result["asymptote"] == {"id1": b"hash1", "id2": b"hash2"}


def test_latest_version_reads_pypi_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """latest_version() extracts the version from the PyPI JSON API response,
    and returns None (rather than raising) when the request fails."""
    import requests

    class FakeResponse:
        @staticmethod
        def json() -> dict:
            return {"info": {"version": "9.9.9"}}

    monkeypatch.setattr(requests, "get", lambda url, timeout: FakeResponse())
    assert utils.latest_version() == "9.9.9"

    def raise_error(url: str, timeout: int) -> None:
        raise requests.ConnectionError("no network")

    monkeypatch.setattr(requests, "get", raise_error)
    assert utils.latest_version() is None


def test_url_for_access(monkeypatch: pytest.MonkeyPatch) -> None:
    """Private access yields a localhost URL (unless running in a GitHub
    codespace, where the forwarded-port domain is used instead)."""
    monkeypatch.delenv("CODESPACES", raising=False)
    assert utils.url_for_access("private", 8000) == "http://localhost:8000"

    monkeypatch.setenv("CODESPACES", "true")
    monkeypatch.setenv("CODESPACE_NAME", "mybox")
    monkeypatch.setenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    assert utils.url_for_access("private", 8000) == "https://mybox-8000.app.github.dev"


def test_binding_for_access() -> None:
    """Private access binds to localhost; public access to all interfaces."""
    assert utils.binding_for_access("private") == "localhost"
    assert utils.binding_for_access("public") == "0.0.0.0"


def test_cannot_find_project(tmp_path: Path) -> None:
    """cannot_find_project() is True (and logs help) only when no project.ptx
    exists in the working directory or any of its ancestors."""
    with utils.working_directory(tmp_path):
        assert utils.cannot_find_project(task="build")
        (tmp_path / "project.ptx").write_text("")
        assert not utils.cannot_find_project(task="build")
