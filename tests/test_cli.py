import json
import subprocess
import os
import shutil
import time
import random
import sys
from pathlib import Path
from contextlib import contextmanager
import requests
import pretext
from pretext import constants
from typing import cast, Generator
from pytest_console_scripts import ScriptRunner
from .common import DEMO_MAPPING

EXAMPLES_DIR = Path(__file__).parent / "examples"

PTX_CMD = cast(str, shutil.which("pretext"))
assert PTX_CMD is not None
PY_CMD = sys.executable


@contextmanager
def pretext_view(*args: str) -> Generator:
    process = subprocess.Popen(
        [PTX_CMD, "-v", "debug", "view", "--no-launch"] + list(args)
    )
    time.sleep(5)  # stall for possible build
    try:
        yield process
    finally:
        process.terminate()
        process.wait()


def test_entry_points(script_runner: ScriptRunner) -> None:
    ret = script_runner.run([PTX_CMD, "-v", "debug", "-h"])
    assert ret.success
    assert (
        subprocess.run(
            [PY_CMD, "-m", "pretext", "-v", "debug", "-h"], shell=True
        ).returncode
        == 0
    )


def test_version(script_runner: ScriptRunner) -> None:
    ret = script_runner.run([PTX_CMD, "-v", "debug", "--version"])
    assert ret.stdout.strip() == pretext.VERSION


def test_new(tmp_path: Path, script_runner: ScriptRunner) -> None:
    assert script_runner.run([PTX_CMD, "-v", "debug", "new"], cwd=tmp_path).success
    # ensure sufficient permissions (n.b. 0oABC expresses integers in octal)
    assert (tmp_path / "new-pretext-project").stat().st_mode % 0o1000 >= 0o755
    for resource in constants.PROJECT_RESOURCES:
        assert (
            tmp_path / "new-pretext-project" / constants.PROJECT_RESOURCES[resource]
        ).exists()


def test_devscript(script_runner: ScriptRunner) -> None:
    """
    Test that `pretext devscript -h` aliases `python /path/to/.ptx/pretext/pretext -h`.
    """
    result = script_runner.run([PTX_CMD, "devscript", "-h"])
    assert result.success
    assert "PreTeXt utility script" in result.stdout


def test_build(tmp_path: Path, script_runner: ScriptRunner) -> None:
    path_with_spaces = "test path with spaces"
    project_path = tmp_path / path_with_spaces
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "demo", "-d", path_with_spaces], cwd=tmp_path
    ).success

    # Do a subset build before the main build, to check that not everything is built on the subset.
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web", "-x", "ch-first-without-spaces"],
        cwd=project_path,
    ).success
    assert (project_path / "output" / "web").exists()
    # ensure sufficient permissions (n.b. 0oABC expresses integers in octal)
    assert (project_path / "output" / "web").stat().st_mode % 0o1000 >= 0o755
    assert not (project_path / "output" / "web" / "ch-empty.html").exists()
    assert (project_path / "output" / "web" / "ch-first-without-spaces.html").exists()
    # Also do a subset without assets
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web", "-x", "sec-latex-image", "-q"],
        cwd=project_path,
    ).success
    assert not (project_path / "generated-assets" / "latex-image").exists()
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web", "-x", "sec-latex-image"],
        cwd=project_path,
    ).success
    assert (project_path / "generated-assets" / "latex-image").exists()

    # Do a full build.
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web"], cwd=project_path
    ).success
    web_path = project_path / "output" / "web"
    assert web_path.exists()
    mapping = json.load(open(web_path / ".mapping.json"))
    print(mapping)
    # This mapping will vary if the project structure produced by ``pretext new`` changes. Be sure to keep these in sync!
    #
    # The path separator varies by platform.
    assert mapping == DEMO_MAPPING


def test_init(tmp_path: Path, script_runner: ScriptRunner) -> None:
    assert script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path).success
    for resource in constants.PROJECT_RESOURCES:
        assert (
            tmp_path / constants.PROJECT_RESOURCES[resource]
        ).exists()


def test_generate_asymptote(tmp_path: Path, script_runner: ScriptRunner) -> None:
    assert script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path).success
    (tmp_path / "source").mkdir()
    shutil.copyfile(EXAMPLES_DIR / "asymptote.ptx", tmp_path / "source" / "main.ptx")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "asymptote"], cwd=tmp_path
    ).success
    assert (tmp_path / "generated-assets" / "asymptote" / "test.html").exists()
    os.remove(tmp_path / "generated-assets" / "asymptote" / "test.html")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "-x", "test"], cwd=tmp_path
    ).success
    assert (tmp_path / "generated-assets" / "asymptote" / "test.html").exists()
    os.remove(tmp_path / "generated-assets" / "asymptote" / "test.html")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "asymptote", "-t", "web"], cwd=tmp_path
    ).success
    os.remove(tmp_path / "generated-assets" / "asymptote" / "test.html")


# @pytest.mark.skip(
#     reason="Waiting on upstream changes to interactive preview generation"
# )
def test_generate_interactive(tmp_path: Path, script_runner: ScriptRunner) -> None:
    int_path = tmp_path / "interactive"
    shutil.copytree(EXAMPLES_DIR / "projects" / "interactive", int_path)
    script_runner.run([PTX_CMD, "-v", "debug", "view", "-s"])
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "-t", "pdf"], cwd=int_path
    ).success
    preview_file = (
        int_path / "generated-assets" / "preview" / "interactive-infinity-preview.png"
    )
    qrcode_file = int_path / "generated-assets" / "qrcode" / "interactive-infinity.png"
    assert preview_file.exists()
    assert qrcode_file.exists()


def test_view(tmp_path: Path, script_runner: ScriptRunner) -> None:
    os.chdir(tmp_path)
    assert script_runner.run([PTX_CMD, "-v", "debug", "new", "-d", "1"]).success
    os.chdir(Path("1"))
    assert script_runner.run([PTX_CMD, "-v", "debug", "build"]).success
    port = random.randint(10_000, 65_536)
    with pretext_view("-p", f"{port}"):
        r = requests.get(f"http://localhost:{port}")
        assert r.status_code == 200
        assert script_runner.run([PTX_CMD, "-v", "debug", "view", "-s"]).success


def test_custom_xsl(tmp_path: Path, script_runner: ScriptRunner) -> None:
    custom_path = tmp_path / "custom"
    shutil.copytree(EXAMPLES_DIR / "projects" / "custom-xsl", custom_path)
    assert script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=custom_path).success
    assert (custom_path / "output" / "test").exists()


def test_custom_webwork_server(tmp_path: Path, script_runner: ScriptRunner) -> None:
    custom_path = tmp_path / "custom"
    shutil.copytree(EXAMPLES_DIR / "projects" / "custom-wwserver", custom_path)
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "webwork"], cwd=custom_path
    )
    assert result.success
    assert "webwork.runestone.academy" in result.stderr
    result = script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=custom_path)
    assert result.success


def test_slideshow(tmp_path: Path, script_runner: ScriptRunner) -> None:
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "slideshow", "-d", "."], cwd=tmp_path
    ).success
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web"], cwd=tmp_path
    ).success
    assert (tmp_path / "output" / "web" / "slides.html").exists()


def test_deploy(tmp_path: Path, script_runner: ScriptRunner) -> None:
    custom_path = tmp_path / "deploy"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", custom_path
    )
    result = script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=custom_path)
    assert result.success
    assert (custom_path / "build" / "here" / "web" / "index.html").exists()
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "deploy", "--stage-only"], cwd=custom_path
    )
    assert result.success
    assert (custom_path / "build" / "here" / "staging" / "index.html").exists()
    assert (
        "hi mom"
        in (custom_path / "build" / "here" / "staging" / "index.html").read_text()
    )
