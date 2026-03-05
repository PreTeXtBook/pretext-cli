import os
from pathlib import Path
from pretext import utils


def test_working_directory(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    subdir = Path("foobar")
    subdir.mkdir()
    assert Path().resolve() == tmp_path.resolve()
    with utils.working_directory(subdir):
        assert Path().resolve().parent == tmp_path.resolve()
    # TODO check path returns afterward


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
        assert utils.requirements_version(tmp_path) is None, f"Should not match: {line!r}"
