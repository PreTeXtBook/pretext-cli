import time
import json
from pathlib import Path
import requests
import shutil
import subprocess
from typing import List

import pytest

from pretext.project import refactor as pr
from pretext import templates
from pretext import utils


EXAMPLES_DIR = Path(__file__).parent / "examples"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# Return True if the given binary is installed and exits with a return code of 0; otherwise, return False. This provides an easy way to check that a given binary is installed.
def check_installed(
    # The command to run to check that a given binary is installed; for example, `["python", "--version"]` would check that Python is installed.
    subprocess_args: List[str],
) -> bool:
    try:
        subprocess.run(subprocess_args, check=True)
    except Exception:
        return False
    return True


HAS_XELATEX = check_installed(["xelatex", "--version"])


# This "test" simply produces a skipped test to inform the developer that xelatex wasn't found, or does nothing if xelatex was found.
@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Note: several tests are skipped, since xelatex wasn't installed.",
)
def test_note_if_no_xelatex() -> None:
    pass


def test_defaults(tmp_path: Path) -> None:
    # This test fails if there happens to be a publication.ptx in publication/. So, switch to a clean directory to avoid this.
    with utils.working_directory(tmp_path):
        ts = ("web", "html"), ("print", "pdf")
        project = pr.Project(ptx_version="2")
        for t in ts:
            project.new_target(*t)
        with templates.resource_path("publication.ptx") as pub_path:
            pass
        assert project._path == Path("project.ptx").resolve()
        assert project.source == Path("source")
        assert project.publication == Path("publication")
        assert project.output == Path("output")
        assert project.site == Path("site")
        assert project.xsl == Path("xsl")
        for t in ts:
            name, frmt = t
            target = project.get_target(name)
            assert target.name == name
            assert target.format == frmt
            assert target.source == Path("main.ptx")
            assert target.publication == pub_path
            assert target.output == Path(name)
            assert target.site == Path("site")
            assert target.xsl is None
            assert target.latex_engine == pr.LatexEngine.XELATEX
            assert target.stringparams == {}


def test_serve(tmp_path: Path) -> None:
    with utils.working_directory(tmp_path):
        port = 12_345
        project = pr.Project(ptx_version="2")
        for mode in ["output", "site"]:
            if mode == "output":
                dir = project.output
            else:
                dir = project.site
            # mypy seems `mode` as a str, so the type check fails.
            p = project.server_process(mode=mode, port=port, launch=False)  # type: ignore
            p.start()
            time.sleep(1)
            assert not (dir / "index.html").exists()
            r = requests.get(f"http://localhost:{port}/index.html")
            assert r.status_code == 404
            dir.mkdir()
            with open(dir / "index.html", "w") as index_file:
                print("<html></html>", file=index_file)
            assert (dir / "index.html").exists()
            r = requests.get(f"http://localhost:{port}/index.html")
            assert r.status_code == 200
            p.terminate()


def test_manifest_simple(tmp_path: Path) -> None:
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 2

        assert project.get_target("web") is not None
        assert project.get_target("web").format == "html"
        assert project.get_target("web").site == Path("site")

        assert project.get_target("print") is not None
        assert project.get_target("print").format == "pdf"
        assert project.get_target("print").site == Path("site")

        assert not project.has_target("foo")

        default_project = pr.Project(ptx_version="2")
        assert default_project.site == project.site
        assert default_project.output == project.output
        assert default_project._path == project._path


def test_manifest_simple_build(tmp_path: Path) -> None:
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        project.get_target("web").build()
        assert (prj_path / "output" / "web" / "index.html").exists()
        if HAS_XELATEX:
            project.get_target("print").build()
            assert (prj_path / "output" / "print" / "main.pdf").exists()


def test_manifest_elaborate(tmp_path: Path) -> None:
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 2

        assert project._path == Path("project.ptx").resolve()
        assert project.source == Path("my_ptx_source")
        assert project.publication == Path("dont-touch")
        assert project.output == Path("build", "here")
        assert project.site == Path("build", "staging")
        assert project.xsl == Path("customizations")
        assert project._executables.xelatex == "xelatex"
        assert project._executables.liblouis == "foobar"

        t_web = project.get_target("web")
        assert t_web.format == "html"
        assert t_web.source == Path("book.ptx")
        assert t_web.publication == Path("publication.ptx")
        assert t_web.output == Path("web")
        assert t_web.site == Path("")
        assert t_web.xsl == Path("silly.xsl")
        assert t_web.stringparams == {}

        t_print = project.get_target("print")
        assert t_print.format == "pdf"
        assert t_print.source == Path("main.ptx")
        assert t_print.publication == Path("extras", "print.xml")
        assert t_print.output == Path("my-pdf")
        assert t_print.site == Path("site")
        assert t_print.xsl is None
        assert t_print.stringparams == {
            "foo": "bar",
            "baz": "goo",
        }


def test_manifest_elaborate_build(tmp_path: Path) -> None:
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        project.get_target("web").build()
        assert (prj_path / "build" / "here" / "web" / "index.html").exists()
        if HAS_XELATEX:
            project.get_target("print").build()
            assert (prj_path / "build" / "here" / "my-pdf" / "main.pdf").exists()


def test_manifest_legacy() -> None:
    prj_path = EXAMPLES_DIR / "projects" / "project_refactor" / "legacy"
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 3

        assert project._executables.xelatex == "xelatex"
        assert project._executables.liblouis == "foobar"

        t_html = project.get_target("html")
        assert t_html is not None
        assert t_html.format == "html"
        assert t_html.source == Path("source", "main.ptx")
        assert t_html.publication == Path("publication", "publication.ptx")
        assert t_html.output == Path("output", "html")
        assert t_html.latex_engine == "xelatex"

        t_latex = project.get_target("latex")
        assert t_latex.format == "latex"
        assert t_latex.source == Path("source", "main.ptx")
        assert t_latex.publication == Path("publication", "publication.ptx")
        assert t_latex.output == Path("output", "latex")
        assert t_latex.latex_engine == "xelatex"

        t_pdf = project.get_target("pdf")
        assert t_pdf.format == "pdf"
        assert t_pdf.source == Path("source", "main.ptx")
        assert t_pdf.publication == Path("publication", "publication.ptx")
        assert t_pdf.output == Path("output", "pdf")
        assert t_pdf.latex_engine == "pdflatex"

        assert not project.has_target("foo")


def test_demo_html_build(tmp_path: Path) -> None:
    path_with_spaces = "test path with spaces"
    project_path = tmp_path / path_with_spaces
    shutil.copytree(TEMPLATES_DIR / "demo", project_path)
    with utils.working_directory(project_path):
        p = pr.Project(ptx_version="2")
        p.new_target("web", "html")
        t_web = p.get_target("web")
        shutil.rmtree(t_web.generated_dir_abspath(), ignore_errors=True)
        t_web.build()
        assert t_web.output_abspath().exists()
        assert (
            t_web.generated_dir_abspath() / "play-button" / "play-button.png"
        ).exists()
        with open(t_web.output_abspath() / ".mapping.json") as mpf:
            mapping = json.load(mpf)
        # This mapping will vary if the project structure produced by ``pretext new`` changes. Be sure to keep these in sync!
        assert mapping == {
            str(Path("source", "main.ptx")): ["my-demo-book"],
            str(Path("source", "frontmatter.ptx")): [
                "frontmatter",
                "frontmatter-preface",
            ],
            str(Path("source", "ch-first with spaces.ptx")): [
                "ch-first-without-spaces"
            ],
            str(Path("source", "sec-first-intro.ptx")): ["sec-first-intro"],
            str(Path("source", "sec-first-examples.ptx")): ["sec-first-examples"],
            str(Path("source", "ex-first.ptx")): ["ex-first"],
            str(Path("source", "ch-empty.ptx")): ["ch-empty"],
            str(Path("source", "ch-features.ptx")): ["ch-features"],
            str(Path("source", "sec-features.ptx")): ["sec-features-blocks"],
            str(Path("source", "backmatter.ptx")): ["backmatter"],
            str(Path("source", "ch-generate.ptx")): [
                "ch-generate",
                "webwork",
                "youtube",
                "interactive-infinity",
                "codelens",
            ],
        }


def test_subset_build(tmp_path: Path) -> None:
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        target = project.get_target("web")
        target.build(xmlid="sec-first")
        assert (target.output_dir_abspath() / "sec-first.html").exists()
        assert not (target.output_dir_abspath() / "index.html").exists()


def test_zip_build(tmp_path: Path) -> None:
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        target = project.get_target("web")
        target.compression = pr.Compression.ZIP
        target.build()
        assert (target.output_dir_abspath() / "book.zip").exists()
        assert not (target.output_dir_abspath() / "index.html").exists()


def test_asset_table(tmp_path: Path) -> None:
    prj_path = tmp_path / "assets"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "assets", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        web = project.get_target("web")
        same_as_web = project.get_target("same-as-web")
        different_than_web = project.get_target("different-than-web")
        assert web.generate_asset_table() == same_as_web.generate_asset_table()
        assert web.generate_asset_table() != different_than_web.generate_asset_table()
