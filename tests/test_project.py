import time
from pathlib import Path
import requests
import shutil
from pretext import project_refactor as pr
from pretext import utils


EXAMPLES_DIR = Path(__file__).parent / "examples"


def test_defaults() -> None:
    ts = ("web", "html"), ("print", "pdf")
    project = pr.Project()
    for t in ts:
        project.add_target(*t)
    assert project.path == Path()
    assert project.source == Path("source")
    assert project.publication == Path("publication")
    assert project.output == Path("output")
    assert project.deploy == Path("deploy")
    assert project.xsl == Path("xsl")
    for t in ts:
        name, frmt = t
        target = project.target(name)
        assert target.name == name
        assert target.format == frmt
        assert target.source == Path("main.ptx")
        assert target.publication == Path("publication.ptx")
        assert target.output == Path(target.name)
        assert target.deploy is None
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
    project.deploy = "bar"
    assert project.deploy == Path("bar")
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
        for mode in ["output", "deploy"]:
            if mode == "output":
                dir = project.output
            else:
                dir = project.deploy
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
        assert project.target("web").deploy is None

        assert project.target("print") is not None
        assert project.target("print").format == "pdf"
        assert project.target("print").deploy is None

        assert project.target("foo") is None

        default_project = pr.Project()
        assert default_project.deploy == project.deploy
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
        assert project.deploy == Path("build", "staging")
        assert project.xsl == Path("customizations")

        assert project.target("web") is not None
        assert project.target("web").format == "html"
        assert project.target("web").source == Path("book.ptx")
        assert project.target("web").publication == Path("publication.ptx")
        assert project.target("web").output == Path("web")
        assert project.target("web").deploy == Path("")
        assert project.target("web").xsl == Path("silly.xsl")
        assert project.target("web").stringparams == {}

        assert project.target("print") is not None
        assert project.target("print").format == "pdf"
        assert project.target("print").source == Path("main.ptx")
        assert project.target("print").publication == Path("extras", "print.xml")
        assert project.target("print").output == Path("my-pdf")
        assert project.target("print").deploy is None
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
