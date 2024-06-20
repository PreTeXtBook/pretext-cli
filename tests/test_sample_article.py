import shutil
import pytest
from pathlib import Path
from pretext.project import Project
from pretext.resources import resource_base_path
import pretext.utils
from .common import check_installed


@pytest.mark.skipif(
    not check_installed(["xelatex", "--version"]),
    reason="Note: several tests are skipped, since xelatex wasn't installed.",
)
def test_sample_article(tmp_path: Path) -> None:
    prj_path = tmp_path / "sample"
    shutil.copytree(
        resource_base_path() / "core" / "examples" / "sample-article", prj_path
    )
    with pretext.utils.working_directory(prj_path):
        project = Project.parse()
        t = project.get_target()
        t.build()
