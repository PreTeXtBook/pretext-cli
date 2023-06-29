import time
import json
import os
from pathlib import Path
import requests
import shutil
from pretext import project_refactor as pr
from pretext import utils


EXAMPLES_DIR = Path(__file__).parent / "examples"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_defaults() -> None:
    ts = ("web", "html"), ("print", "pdf")
    project = pr.Project()
    for t in ts:
        project.add_target(*t)
    assert project.path == Path()
    assert project.source == Path("source")
    assert project.publication == Path("publication")
    assert project.output == Path("output")
    assert project.site == Path("site")
    assert project.xsl == Path("xsl")
    for t in ts:
        name, frmt = t
        target = project.target(name)
        assert target.name == name
        assert target.format == frmt
        assert target.source == Path("main.ptx")
        assert target.publication == Path("publication.ptx")
        assert target.output == Path(target.name)
        assert target.site is None
        assert target.xsl is None
        assert target.latex_engine == "xelatex"
        assert target.stringparams == {}


def test_modifications() -> None:
    ts = ("web", "html"), ("print", "pdf")
    project = pr.Project()
    for t in ts:
        project.add_target(*t)
    project.source = Path("foo")
    assert project.source == Path("foo")
    project.site = "bar"
    assert project.site == Path("bar")
    project.publication = None
    assert project.publication == Path("publication")
    for t in ts:
        name, _ = t
        target = project.target(name)
        target.source = "foo.ptx"
        assert target.source == Path("foo.ptx")
        target.publication = Path("bar.ptx")
        assert target.publication == Path("bar.ptx")
        target.output = None
        assert target.output == Path(target.name)


def test_serve(tmp_path: Path) -> None:
    with utils.working_directory(tmp_path):
        port = 12_345
        project = pr.Project()
        for mode in ["output", "site"]:
            if mode == "output":
                dir = project.output
            else:
                dir = project.site
            p = project.server_process(mode=mode, port=port, launch=False)
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

        assert project.target("web") is not None
        assert project.target("web").format == "html"
        assert project.target("web").site is None

        assert project.target("print") is not None
        assert project.target("print").format == "pdf"
        assert project.target("print").site is None

        assert project.target("foo") is None

        default_project = pr.Project()
        assert default_project.site == project.site
        assert default_project.output == project.output
        assert default_project.path == project.path


def test_manifest_simple_build(tmp_path: Path) -> Path:
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        project.target("web").build()
        assert (prj_path / "output" / "web" / "index.html").exists()
        project.target("print").build()
        assert (prj_path / "output" / "print" / "main.pdf").exists()


def test_manifest_elaborate(tmp_path: Path) -> None:
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 2

        assert project.path == Path()
        assert project.source == Path("my_ptx_source")
        assert project.publication == Path("dont-touch")
        assert project.output == Path("build", "here")
        assert project.site == Path("build", "staging")
        assert project.xsl == Path("customizations")
        assert project.executables.get("xelatex") == "xelatex"
        assert project.executables.get("liblouis") == "foobar"
        assert project.executables.get("baz") is None

        assert project.target("web") is not None
        assert project.target("web").format == "html"
        assert project.target("web").source == Path("book.ptx")
        assert project.target("web").publication == Path("publication.ptx")
        assert project.target("web").output == Path("web")
        assert project.target("web").site == Path("")
        assert project.target("web").xsl == Path("silly.xsl")
        assert project.target("web").stringparams == {}

        assert project.target("print") is not None
        assert project.target("print").format == "pdf"
        assert project.target("print").source == Path("main.ptx")
        assert project.target("print").publication == Path("extras", "print.xml")
        assert project.target("print").output == Path("my-pdf")
        assert project.target("print").site is None
        assert project.target("print").xsl is None
        assert project.target("print").stringparams == {
            "foo": "bar",
            "baz": "goo",
        }


def test_manifest_elaborate_build(tmp_path: Path) -> Path:
    prj_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", prj_path
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        project.target("web").build()
        assert (prj_path / "build" / "here" / "web" / "index.html").exists()
        project.target("print").build()
        assert (prj_path / "build" / "here" / "my-pdf" / "main.pdf").exists()


def test_manifest_legacy() -> None:
    prj_path = EXAMPLES_DIR / "projects" / "project_refactor" / "legacy"
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 3

        assert project.executables.get("xelatex") == "xelatex"
        assert project.executables.get("liblouis") == "foobar"
        assert project.executables.get("baz") is None

        assert project.target("html") is not None
        assert project.target("html").format == "html"
        assert project.target("html").source == Path("source", "main.ptx")
        assert project.target("html").publication == Path(
            "publication", "publication.ptx"
        )
        assert project.target("html").output == Path("output", "html")
        assert project.target("html").latex_engine == "xelatex"

        assert project.target("latex") is not None
        assert project.target("latex").format == "latex"
        assert project.target("latex").source == Path("source", "main.ptx")
        assert project.target("latex").publication == Path(
            "publication", "publication.ptx"
        )
        assert project.target("latex").output == Path("output", "latex")
        assert project.target("latex").latex_engine == "xelatex"

        assert project.target("pdf") is not None
        assert project.target("pdf").format == "pdf"
        assert project.target("pdf").source == Path("source", "main.ptx")
        assert project.target("pdf").publication == Path(
            "publication", "publication.ptx"
        )
        assert project.target("pdf").output == Path("output", "pdf")
        assert project.target("pdf").latex_engine == "pdflatex"

        assert project.target("foo") is None


def test_demo_build(tmp_path: Path) -> None:
    path_without_spaces = "test-path-without-spaces"
    project_path = tmp_path / path_without_spaces
    shutil.copytree(TEMPLATES_DIR / "demo", project_path)
    # shutil.rmtree(project_path / "generated-assets", ignore_errors=True)
    with utils.working_directory(project_path):
        p = pr.Project()
        p.add_target("web", "html")
        p.add_target("print", "pdf")
        p.target("web").build()  # TODO this is not generating assets...
        assert p.target("web").output_abspath().exists()
        with open(p.target("web").output_abspath() / ".mapping.json") as mpf:
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
        target = project.target("web")
        target.build(xmlid_root="sec-first")
        assert (target.output_dir_abspath() / "sec-first.html").exists()
        assert not (target.output_dir_abspath() / "index.html").exists()


def test_assets(tmp_path: Path) -> None:
    prj_path = tmp_path / "assets"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "assets", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        web = project.target("web")
        same_as_web = project.target("same-as-web")
        different_than_web = project.target("different-than-web")
        assert web.generate_asset_table() == same_as_web.generate_asset_table()
        assert web.generate_asset_table() != different_than_web.generate_asset_table()
