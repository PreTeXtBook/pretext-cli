import multiprocessing, time
from pathlib import Path
import requests
from pretext import project_refactor as pr
from pretext import templates, utils

def test_defaults() -> None:
    ts = ("web","HTML"), ("print","PDF")
    targets = [pr.Target(*t) for t in ts]
    project = pr.Project(targets)
    assert project.path == Path()
    assert project.output == Path() / "output"
    assert project.deploy == Path() / "deploy"
    for t in ts:
        name,frmt = t
        target = project.target(name)
        assert target.name == name
        assert target.format == frmt
        assert target.source == Path("source", "main.ptx")
        assert target.publication is None
        assert target.external_dir == Path("assets")
        assert target.generated_dir == Path("generated-assets")
        assert target.output == Path("output", target.name)
        assert target.deploy is None
        assert target.latex_engine == "XELATEX"

def test_serve(tmp_path: Path) -> None:
    with utils.working_directory(tmp_path):
        port = 12_345
        project = pr.Project([])
        for mode in ["OUTPUT", "DEPLOY"]:
            if mode == "OUTPUT":
                dir = project.output
            else:
                dir = project.deploy
            p = project.server_process(mode=mode,port=port,launch=False)
            p.start()
            time.sleep(3)
            assert not (dir / "index.html").exists()
            r = requests.get(f"http://localhost:{port}/index.html")
            assert r.status_code == 404
            dir.mkdir()
            with open(dir / "index.html", "w") as index_file:
                print("<html></html>",file=index_file)
            assert (dir / "index.html").exists()
            r = requests.get(f"http://localhost:{port}/index.html")
            assert r.status_code == 200
            p.terminate()

