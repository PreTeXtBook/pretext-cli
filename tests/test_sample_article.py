import shutil
import pytest
from pathlib import Path
import errorhandler  # type: ignore
from pretext.project import Project
import pretext.utils
from .common import check_installed, EXAMPLES_DIR


@pytest.mark.skipif(
    not check_installed(["xelatex", "--version"]),
    reason="Note: several tests are skipped, since xelatex wasn't installed.",
)
def test_sample_article(tmp_path: Path) -> None:
    error_checker = errorhandler.ErrorHandler(logger="ptxlogger")
    prj_path = tmp_path / "sample"
    shutil.copytree(EXAMPLES_DIR / "core" / "examples" / "sample-article", prj_path)
    with pretext.utils.working_directory(prj_path):
        project = Project.parse()
        t = project.get_target()
        t.build()
        assert not error_checker.fired
