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

EXAMPLES_DIR = Path(__file__).parent / "examples"

PTX_CMD = shutil.which("pretext")
PY_CMD = sys.executable


@contextmanager
def pretext_view(*args):
    process = subprocess.Popen(
        [PTX_CMD, "-v", "debug", "view", "--no-launch"] + list(args)
    )
    time.sleep(3)  # stall for possible build
    try:
        yield process
    finally:
        process.terminate()
        process.wait()


def test_entry_points(script_runner):
    ret = script_runner.run(PTX_CMD, "-v", "debug", "-h")
    assert ret.success
    assert (
        subprocess.run(
            [PY_CMD, "-m", "pretext", "-v", "debug", "-h"], shell=True
        ).returncode
        == 0
    )


def test_version(script_runner):
    ret = script_runner.run(PTX_CMD, "-v", "debug", "--version")
    assert ret.stdout.strip() == pretext.VERSION


def test_new(tmp_path: Path, script_runner):
    assert script_runner.run(PTX_CMD, "-v", "debug", "new", cwd=tmp_path).success
    assert (tmp_path / "new-pretext-project" / "project.ptx").exists()


def test_core(script_runner):
    """
    Test that `pretext core -h` aliases `python /path/to/.ptx/pretext/pretext -h`.
    """
    result = script_runner.run(PTX_CMD, "core", "-h")
    assert result.success
    assert "PreTeXt utility script" in result.stdout


def test_build(tmp_path: Path, script_runner):
    path_with_spaces = "test path with spaces"
    project_path = tmp_path / path_with_spaces
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "new", "demo", "-d", path_with_spaces, cwd=tmp_path
    ).success
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "build", "web", cwd=project_path
    ).success
    web_path = project_path / "output" / "web"
    assert web_path.exists()
    mapping = json.load(open(web_path / ".mapping.json"))
    print(mapping)
    # This mapping will vary if the project structure produced by ``pretext new`` changes. Be sure to keep these in sync!
    #
    # The path separator varies by platform.
    source_prefix = f"source{os.sep}"
    assert mapping == {
        f"{source_prefix}main.ptx": ["my-demo-book"],
        f"{source_prefix}frontmatter.ptx": [
            "frontmatter",
            "frontmatter-preface",
        ],
        f"{source_prefix}ch-first with spaces.ptx": ["ch-first-without-spaces"],
        f"{source_prefix}sec-first-intro.ptx": ["sec-first-intro"],
        f"{source_prefix}sec-first-examples.ptx": ["sec-first-examples"],
        f"{source_prefix}ex-first.ptx": ["ex-first"],
        f"{source_prefix}ch-empty.ptx": ["ch-empty"],
        f"{source_prefix}ch-features.ptx": ["ch-features"],
        f"{source_prefix}sec-features.ptx": ["sec-features-blocks"],
        f"{source_prefix}backmatter.ptx": ["backmatter"],
    }
    assert script_runner.run(
        PTX_CMD,
        "-v",
        "debug",
        "build",
        "subset",
        "-x",
        "ch-first-without-spaces",
        cwd=project_path,
    ).success
    assert (project_path / "output" / "subset").exists()
    assert not (project_path / "output" / "subset" / "ch-empty.html").exists()
    assert (
        project_path / "output" / "subset" / "ch-first-without-spaces.html"
    ).exists()
    assert script_runner.run(PTX_CMD, "build", "print-latex", cwd=project_path).success
    assert (project_path / "output" / "print-latex").exists()
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "build", "-g", cwd=project_path
    ).success
    assert (project_path / "generated-assets").exists()
    os.removedirs(project_path / "generated-assets")
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "build", "-g", "webwork", cwd=project_path
    ).success
    assert (project_path / "generated-assets").exists()


def test_init(tmp_path: Path, script_runner):
    assert script_runner.run(PTX_CMD, "-v", "debug", "init", cwd=tmp_path).success
    assert (tmp_path / "project.ptx").exists()
    assert (tmp_path / "requirements.txt").exists()
    assert (tmp_path / ".gitignore").exists()
    assert (tmp_path / "publication" / "publication.ptx").exists()
    assert len([*tmp_path.glob("project-*.ptx")]) == 0  # need to refresh
    assert script_runner.run(PTX_CMD, "-v", "debug", "init", "-r", cwd=tmp_path).success
    assert len([*tmp_path.glob("project-*.ptx")]) > 0
    assert len([*tmp_path.glob("requirements-*.txt")]) > 0
    assert len([*tmp_path.glob(".gitignore-*")]) > 0
    assert len([*tmp_path.glob("publication/publication-*.ptx")]) > 0


def test_generate_asymptote(tmp_path: Path, script_runner):
    assert script_runner.run(PTX_CMD, "-v", "debug", "init", cwd=tmp_path).success
    (tmp_path / "source").mkdir()
    shutil.copyfile(EXAMPLES_DIR / "asymptote.ptx", tmp_path / "source" / "main.ptx")
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "generate", "asymptote", cwd=tmp_path
    ).success
    assert (tmp_path / "generated-assets" / "asymptote" / "test.html").exists()
    os.remove(tmp_path / "generated-assets" / "asymptote" / "test.html")
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "generate", "-x", "test", cwd=tmp_path
    ).success
    assert (tmp_path / "generated-assets" / "asymptote" / "test.html").exists()
    os.remove(tmp_path / "generated-assets" / "asymptote" / "test.html")
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "generate", "asymptote", "-t", "web", cwd=tmp_path
    ).success
    os.remove(tmp_path / "generated-assets" / "asymptote" / "test.html")


# @pytest.mark.skip(
#     reason="Waiting on upstream changes to interactive preview generation"
# )
def test_generate_interactive(tmp_path: Path, script_runner):
    int_path = tmp_path / "interactive"
    shutil.copytree(EXAMPLES_DIR / "projects" / "interactive", int_path)
    assert script_runner.run(PTX_CMD, "-v", "debug", "generate", cwd=int_path).success
    preview_file = (
        int_path / "generated-assets" / "preview" / "interactive-infinity-preview.png"
    )
    qrcode_file = int_path / "generated-assets" / "qrcode" / "interactive-infinity.png"
    assert preview_file.exists()
    assert qrcode_file.exists()


def test_view(tmp_path: Path, script_runner):
    os.chdir(tmp_path)
    port = random.randint(10_000, 65_536)
    with pretext_view("-d", ".", "-p", f"{port}"):
        assert requests.get(f"http://localhost:{port}/").status_code == 200
    assert script_runner.run(PTX_CMD, "-v", "debug", "new", "-d", "1").success
    os.chdir(Path("1"))
    assert script_runner.run(PTX_CMD, "-v", "debug", "build").success
    port = random.randint(10_000, 65_536)
    with pretext_view("-p", f"{port}"):
        assert requests.get(f"http://localhost:{port}/").status_code == 200
    os.chdir(tmp_path)
    assert script_runner.run(PTX_CMD, "-v", "debug", "new", "-d", "2").success
    os.chdir(Path("2"))
    port = random.randint(10_000, 65_536)
    with pretext_view("-p", f"{port}", "-b", "-g"):
        assert requests.get(f"http://localhost:{port}/").status_code == 200


def test_custom_xsl(tmp_path: Path, script_runner):
    custom_path = tmp_path / "custom"
    shutil.copytree(EXAMPLES_DIR / "projects" / "custom-xsl", custom_path)
    assert script_runner.run(PTX_CMD, "-v", "debug", "build", cwd=custom_path).success
    assert (custom_path / "output" / "test").exists()


def test_custom_webwork_server(tmp_path: Path, script_runner):
    custom_path = tmp_path / "custom"
    shutil.copytree(EXAMPLES_DIR / "projects" / "custom-wwserver", custom_path)
    result = script_runner.run(
        PTX_CMD, "-v", "debug", "generate", "webwork", cwd=custom_path
    )
    assert result.success
    assert "webwork-dev" in result.stderr
    result = script_runner.run(PTX_CMD, "-v", "debug", "build", cwd=custom_path)
    assert result.success


def test_slideshow(tmp_path: Path, script_runner):
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "new", "slideshow", "-d", ".", cwd=tmp_path
    ).success
    assert script_runner.run(
        PTX_CMD, "-v", "debug", "build", "web", cwd=tmp_path
    ).success
    assert (tmp_path / "output" / "web" / "slides.html").exists()
