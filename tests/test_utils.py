import fnmatch
import os
import sys
import pytest
from pathlib import Path
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
    magic_comment = (
        b"foo\n<!-- Managed automatically by PreTeXt authoring tools -->\nbar"
    )
    assert utils.is_unmodified("foo", magic_comment)


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

    includes: list[str] = config["tool"]["poetry"]["include"]

    core_dir = root / "pretext" / "core"
    core_files = [
        str(p.relative_to(root))
        for p in sorted(core_dir.glob("*.py"))
        if p.name != "__init__.py"
    ]

    for rel_path in core_files:
        covered = any(fnmatch.fnmatch(rel_path, pat) for pat in includes)
        assert covered, (
            f"{rel_path} is not covered by any entry in pyproject.toml [tool.poetry] include.\n"
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
