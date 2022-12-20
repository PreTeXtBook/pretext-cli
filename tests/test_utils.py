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


def test_cached_project_path(tmp_path: Path):
    os.chdir(tmp_path)
    subdir1 = tmp_path / "foobar1"
    subdir1.mkdir()
    subdir2 = tmp_path / "foobar2"
    subdir2.mkdir()
    os.chdir(subdir1)
    Path("project.ptx").write_text("")
    assert Path("project.ptx").exists()
    assert utils.project_path().resolve() == subdir1.resolve()
    with utils.working_directory(subdir2):  # project should be cached as subdir1
        assert utils.project_path() == subdir1.resolve()
