import time
import json
from pathlib import Path
import requests
import shutil

import pydantic
import pytest

from pretext import project as pr
from pretext import utils
from pretext.resources import resource_base_path

from .common import DEMO_MAPPING, EXAMPLES_DIR, check_installed


TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
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
        ts_dict = {}
        project = pr.Project(ptx_version="2")
        for t in ts:
            ts_dict[t[0]] = project.new_target(*t)
        assert project._path == Path.cwd() / Path("project.ptx")
        assert project.source == Path("source")
        assert project.publication == Path("publication")
        assert project.output_dir == Path("output")
        assert project.site == Path("site")
        assert project.xsl == Path("xsl")
        for t in ts:
            name, format = t
            target = project.get_target(name)
            assert target == ts_dict[name]
            assert target.name == name
            assert target.format == format
            assert target.source == Path("main.ptx")
            assert (
                target.publication
                == resource_base_path() / "templates" / "publication.ptx"
            )
            assert target.output_dir == Path(name)
            assert target.deploy_dir is None
            assert target.xsl is None
            assert target.latex_engine == pr.LatexEngine.XELATEX
            assert target.stringparams == {}


def test_serve(tmp_path: Path) -> None:
    with utils.working_directory(tmp_path):
        port = 12_345
        project = pr.Project(ptx_version="2")
        dir = project.output_dir

        p = project.server_process(port=port)
        p.start()
        time.sleep(1)
        assert not (dir / "index.html").exists()
        r = requests.get(f"http://localhost:{port}/{dir}/index.html")
        assert r.status_code == 404
        dir.mkdir()
        with open(dir / "index.html", "w") as index_file:
            print("<html></html>", file=index_file)
        assert (dir / "index.html").exists()
        r = requests.get(f"http://localhost:{port}/{dir}/index.html")
        assert r.status_code == 200
        p.terminate()


def test_manifest_simple(tmp_path: Path) -> None:
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 3

        t_web = project.get_target("web")
        assert t_web.format == "html"
        assert t_web.platform == "web"
        assert t_web.deploy_dir is None

        t_print = project.get_target("print")
        assert t_print.format == "pdf"
        assert t_print.platform is None
        assert t_print.deploy_dir is None

        t_rune = project.get_target("rs")
        assert t_rune.format == "html"
        assert t_rune.platform == "runestone"
        assert t_rune.output_dir_abspath().resolve().relative_to(
            project.abspath()
        ) == Path("published/runestone-document-id")

        assert not project.has_target("foo")

        default_project = pr.Project(ptx_version="2")
        assert default_project.site == project.site
        assert default_project.output_dir == project.output_dir
        assert default_project._path == project._path


def test_manifest_simple_build(tmp_path: Path) -> None:
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        project.get_target("web").build()
        assert (prj_path / "output" / "web" / "index.html").exists()
        project.get_target("rs").build()
        assert (
            prj_path / "published" / "runestone-document-id" / "index.html"
        ).exists()
        assert (
            prj_path / "published" / "runestone-document-id" / "runestone-manifest.xml"
        ).exists()
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
        assert project.output_dir == Path("build", "here")
        assert project.site == Path("my-great-site")
        assert project.xsl == Path("customizations")
        assert project._executables.xelatex == "xelatex"
        assert project._executables.liblouis == "foobar"
        assert project.asy_method == "local"

        t_web = project.get_target("web")
        assert t_web.format == "html"
        assert t_web.source == Path("book.ptx")
        assert t_web.publication == Path("publication.ptx")
        assert t_web.output_dir == Path("web")
        assert t_web.output_dir_abspath().relative_to(project.abspath()) == Path(
            "build/here/web"
        )
        assert t_web.deploy_dir == Path("")
        assert t_web.xsl == Path("silly.xsl")
        assert t_web.stringparams == {}
        assert t_web.asy_method == "server"
        assert sorted(t_web.server, key=lambda k: k.name) == [
            pr.Server(name="asy", url="http://example1.com"),  # type: ignore
            pr.Server(name="sage", url="http://example2.com"),  # type: ignore
        ]

        t_print = project.get_target("print")
        assert t_print.format == "pdf"
        assert t_print.source == Path("main.ptx")
        assert t_print.publication == Path("extras", "print.xml")
        assert t_print.output_dir == Path("my-pdf")
        assert t_print.output_dir_abspath().relative_to(project.abspath()) == Path(
            "build/here/my-pdf"
        )
        assert t_print.output_filename == "out.pdf"
        assert t_print.deploy_dir is None
        assert t_print.xsl is None
        assert t_print.stringparams == {
            "foo": "bar",
            "baz": "goo",
        }
        assert t_print.asy_method == "local"
        assert sorted(t_print.server, key=lambda k: k.name) == [
            pr.Server(name="asy", url="http://example3.com"),  # type: ignore
            pr.Server(name="sage", url="http://example2.com"),  # type: ignore
        ]


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
            assert (prj_path / "build" / "here" / "my-pdf" / "out.pdf").exists()


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
        assert t_html.source_abspath() == project.abspath() / Path("source", "main.ptx")
        assert t_html.publication_abspath() == project.abspath() / Path(
            "publication", "publication.ptx"
        )
        assert t_html.output_dir_abspath() == project.abspath() / Path("output", "html")
        assert t_html.latex_engine == "xelatex"
        assert t_html.stringparams == {"one": "uno", "two": "dos"}

        t_latex = project.get_target("latex")
        assert t_latex.format == "latex"
        assert t_latex.source == Path("source", "main.ptx")
        assert t_latex.publication == Path("publication", "publication.ptx")
        assert t_latex.output_dir == Path("output", "latex")
        assert t_latex.latex_engine == "xelatex"

        t_pdf = project.get_target("pdf")
        assert t_pdf.format == "pdf"
        assert t_pdf.source == Path("source", "main.ptx")
        assert t_pdf.publication == Path("publication", "publication.ptx")
        assert t_pdf.output_dir == Path("output", "pdf")
        assert t_pdf.latex_engine == "pdflatex"

        assert not project.has_target("foo")

        assert project._executables.latex == "latex1"


# Repeat the above test with a manifest that has extra, unknown elements. This should still work, but the extra elements should be ignored.
def test_manifest_legacy_wrong() -> None:
    prj_path = EXAMPLES_DIR / "projects" / "project_refactor" / "legacy_extra"
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 3

        assert project._executables.xelatex == "xelatex"
        assert project._executables.liblouis == "foobar"

        t_html = project.get_target("html")
        assert t_html is not None
        assert t_html.format == "html"
        assert t_html.source_abspath() == project.abspath() / Path("source", "main.ptx")
        assert t_html.publication_abspath() == project.abspath() / Path(
            "publication", "publication.ptx"
        )
        assert t_html.output_dir_abspath() == project.abspath() / Path("output", "html")
        assert t_html.latex_engine == "xelatex"
        assert t_html.stringparams == {"one": "uno", "two": "dos"}

        t_latex = project.get_target("latex")
        assert t_latex.format == "latex"
        assert t_latex.source == Path("source", "main.ptx")
        assert t_latex.publication == Path("publication", "publication.ptx")
        assert t_latex.output_dir == Path("output", "latex")
        assert t_latex.latex_engine == "xelatex"

        t_pdf = project.get_target("pdf")
        assert t_pdf.format == "pdf"
        assert t_pdf.source == Path("source", "main.ptx")
        assert t_pdf.publication == Path("publication", "publication.ptx")
        assert t_pdf.output_dir == Path("output", "pdf")
        assert t_pdf.latex_engine == "pdflatex"

        assert not project.has_target("foo")

        assert project._executables.latex == "latex1"


def test_html_build_permissions(tmp_path: Path) -> None:
    prj_path = tmp_path / "hello"
    shutil.copytree(TEMPLATES_DIR / "hello", prj_path)
    with utils.working_directory(prj_path):
        p = pr.Project(ptx_version="2")
        p.new_target("web", "html").build()
        assert (prj_path / "output" / "web").exists()
        assert (prj_path / "output" / "web").stat().st_mode % 0o1000 >= 0o755


def test_demo_html_build(tmp_path: Path) -> None:
    path_with_spaces = "test path with spaces"
    project_path = tmp_path / path_with_spaces
    shutil.copytree(TEMPLATES_DIR / "demo", project_path)
    with utils.working_directory(project_path):
        p = pr.Project(ptx_version="2")
        t_web = p.new_target("web", "html")
        shutil.rmtree(t_web.generated_dir_abspath(), ignore_errors=True)
        t_web.build()
        assert t_web.output_dir_abspath().exists()
        with open(t_web.output_dir_abspath() / ".mapping.json") as mpf:
            mapping = json.load(mpf)
        # This mapping will vary if the project structure produced by ``pretext new`` changes. Be sure to keep these in sync!
        assert mapping == DEMO_MAPPING


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


def test_deploy(tmp_path: Path) -> None:
    # check permutations of deploy / deploy-dir
    project = pr.Project(ptx_version="2")

    t = project.new_target(
        name="none-deploy-none-dir",
        format="html",
    )
    assert not t.to_deploy()
    assert t.deploy_dir_relpath().name == t.name

    t = project.new_target(
        name="no-deploy-none-dir",
        format="html",
        deploy="no",
    )
    assert not t.to_deploy()
    assert t.deploy_dir_relpath().name == t.name

    t = project.new_target(
        name="yes-deploy-none-dir",
        format="html",
        deploy="yes",
    )
    assert t.to_deploy()
    assert t.deploy_dir_relpath().name == t.name

    t = project.new_target(
        name="none-deploy-custom-dir",
        format="html",
        deploy_dir="custom",
    )
    assert t.to_deploy()
    assert t.deploy_dir_relpath().name == "custom"

    t = project.new_target(
        name="no-deploy-custom-dir",
        format="html",
        deploy="no",
        deploy_dir="custom",
    )
    assert not t.to_deploy()
    assert t.deploy_dir_relpath().name == "custom"

    t = project.new_target(
        name="yes-deploy-custom-dir",
        format="html",
        deploy="yes",
        deploy_dir="custom",
    )
    assert t.to_deploy()
    assert t.deploy_dir_relpath().name == "custom"

    # check elaborate settings
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert project.get_target("web").to_deploy()
        assert not project.get_target("print").to_deploy()
        project.get_target("web").build()
        assert (prj_path / "build" / "here" / "web" / "index.html").exists()
        project.deploy(stage_only=True)
        assert (prj_path / "build" / "here" / "staging" / "index.html").exists()
        assert (
            "hi mom"
            in (prj_path / "build" / "here" / "staging" / "index.html").read_text()
        )


def test_validation(tmp_path: Path) -> None:
    project = pr.Project(ptx_version="2")
    # Verify that repeated server names cause a validation error.
    with pytest.raises(pydantic.ValidationError):
        project.new_target(
            name="test",
            format="html",
            server=[
                pr.Server(name="sage", url="http://test1.com"),  # type: ignore
                pr.Server(name="sage", url="http://test2.com"),  # type: ignore
            ],
        )

    # An output-filename should cause a validation error for specific project types.
    with pytest.raises(pydantic.ValidationError):
        project.new_target(name="test", format="html", output_filename="not-allowed")
    with pytest.raises(pydantic.ValidationError):
        project.new_target(
            name="test",
            format="html",
            platform="runestone",
            output_filename="not-allowed",
        )
    with pytest.raises(pydantic.ValidationError):
        project.new_target(
            name="test", format="html", platform="runestone", output_dir="not-allowed"
        )
    with pytest.raises(pydantic.ValidationError):
        project.new_target(name="test", format="pdf", compression="zip")
    with pytest.raises(pydantic.ValidationError):
        project.new_target(name="test", format="pdf", platform="runestone")
    with pytest.raises(pydantic.ValidationError):
        project.new_target(name="test", format="html", stringparamz="oops")

    # Validation should catch extra elements or attributes in this project file.
    prj_path = tmp_path / "simple_extra_attribute"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "simple_extra_attribute",
        prj_path,
    )
    with utils.working_directory(prj_path):
        with pytest.raises(pydantic.ValidationError):
            pr.Project.parse()

    prj_path = tmp_path / "simple_extra_element"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "simple_extra_element",
        prj_path,
    )
    with utils.working_directory(prj_path):
        with pytest.raises(pydantic.ValidationError):
            pr.Project.parse()


def test_no_knowls(tmp_path: Path) -> None:
    prj_path = tmp_path / "xref"
    shutil.copytree(EXAMPLES_DIR / "projects" / "xref", prj_path)
    with utils.working_directory(prj_path):
        target = pr.Project.parse().get_target("web")
        target.build()
        with open(Path("output") / "web" / "article.html") as article_file:
            contents = article_file.read()
            assert "data-knowl" in contents
        target.build(no_knowls=True)
        with open(Path("output") / "web" / "article.html") as article_file:
            contents = article_file.read()
            assert "data-knowl" not in contents
