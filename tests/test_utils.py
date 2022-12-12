import os
from pathlib import Path
from pretext import utils


def test_working_directory(tmp_path: Path):
    os.chdir(tmp_path)
    subdir = Path("foobar")
    subdir.mkdir()
    assert Path().resolve() == tmp_path.resolve()
    with utils.working_directory(subdir):
        assert Path().resolve().parent == tmp_path.resolve()
    # TODO check path returns afterward


def test_project_path(tmp_path: Path):
    os.chdir(tmp_path)
    Path("project.ptx").write_text("")
    assert Path("project.ptx").exists()
    assert utils.project_path().resolve() == tmp_path.resolve()
    subdir = Path("foobar")
    print(subdir.resolve())
    subdir.mkdir()
    os.chdir(subdir)
    assert utils.project_path().resolve() == Path().resolve().parent
