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
    magic_comment = b"foo\n<!-- Managed automatically by PreTeXt authoring tools -->\nbar"
    assert utils.is_unmodified("foo", magic_comment)
