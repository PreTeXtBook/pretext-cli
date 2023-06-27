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
    assert project.output == Path() / "output"
    assert project.deploy == Path() / "deploy"
    for t in ts:
        name, frmt = t
        target = project.target(name)
        assert target.name == name
        assert target.format == frmt
        assert target.source == Path("main.ptx")
        assert target.publication is None
        assert target.external_dir == Path("assets")
        assert target.generated_dir == Path("generated-assets")
        assert target.output == Path(target.name)
        assert target.deploy is None
        assert target.latex_engine == "xelatex"


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


def test_manifest(tmp_path: Path) -> None:
    prj_path = tmp_path / "project"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 2

        assert project.target("web") is not None
        assert project.target("web").format == "html"
        assert project.target("web").deploy == Path("")

        assert project.target("print") is not None
        assert project.target("print").format == "pdf"
        assert project.target("print").deploy is None

        assert project.target("foo") is None

        default_project = pr.Project()
        assert default_project.deploy == project.deploy
        assert default_project.output == project.output
        assert default_project.path == project.path
