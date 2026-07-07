"""
Full-stack smoke test: build core PreTeXt's own sample article.

The sample article (vendored under ``tests/examples/core``) exercises nearly
every PreTeXt feature -- sage cells, asymptote and latex-image graphics,
webwork, interactives -- so this single build touches far more of the
toolchain than the small fixture projects.  It requires xelatex, asy, and
sage, and is the longest-running test in the suite; it is skipped entirely
when those executables are missing.
"""

import shutil
import pytest
from pathlib import Path
import errorhandler  # type: ignore
from pretext.project import Project
import pretext.utils
from .common import check_installed, EXAMPLES_DIR

HAS_XELATEX = check_installed(["xelatex", "--version"])
HAS_ASY = check_installed(["asy", "--version"])
HAS_SAGE = check_installed(["sage", "--version"])


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Note: several tests are skipped, since xelatex wasn't installed.",
)
@pytest.mark.skipif(
    not HAS_ASY,
    reason="Skipped since asy isn't found.",
)
@pytest.mark.skipif(
    not HAS_SAGE,
    reason="Skipped since sage isn't found.",
)
def test_sample_article(tmp_path: Path) -> None:
    """The sample article builds without a single logged error (an
    errorhandler on the pretext logger turns any log.error into a failure,
    even ones the build would otherwise swallow)."""
    error_checker = errorhandler.ErrorHandler(logger="ptxlogger")
    prj_path = tmp_path / "sample"
    shutil.copytree(EXAMPLES_DIR / "core" / "examples" / "sample-article", prj_path)
    with pretext.utils.working_directory(prj_path):
        project = Project.parse()
        t = project.get_target()
        t.build()
        assert not error_checker.fired
