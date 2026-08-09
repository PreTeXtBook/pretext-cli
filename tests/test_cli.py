"""
End-to-end tests of the `pretext` command line interface.

Every test here invokes the installed ``pretext`` script (via the
pytest-console-scripts ``script_runner`` fixture) exactly the way a user
would, and asserts on exit codes and on files produced on disk.  Tests of
the underlying Python API (`pretext.project.Project` et al.) live in
``test_project.py``; pure-function unit tests live in ``test_utils.py``,
``test_server.py``, ``test_codechat.py``, and ``test_generate.py``.

The file is organized to mirror the CLI's command surface:

1. CLI basics (entry points, --version, devscript, support)
2. Project scaffolding (new, init, update-project)
3. Build (pretext build and its flags)
4. Asset generation (pretext generate and build's -g/-q flags)
5. Validate (pretext validate)
6. View (pretext view and the preview server)
7. Deploy (pretext deploy)
8. Import (pretext import)

Tests that require external executables (xelatex, asymptote, sage) are
skipped when those aren't installed, so the suite degrades gracefully on
developer machines while running fully in the pretext-full CI container.
"""

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
from pretext import constants, resources, server, utils
from typing import cast, Generator, List
import pytest
from pytest_console_scripts import ScriptRunner

# from .common import DEMO_MAPPING, EXAMPLES_DIR, check_installed
from .common import EXAMPLES_DIR, check_installed

PTX_CMD = cast(str, shutil.which("pretext"))
assert PTX_CMD is not None
PY_CMD = sys.executable

HAS_XELATEX = check_installed(["xelatex", "--version"])
HAS_ASY = check_installed(["asy", "--version"])
HAS_SAGE = check_installed(["sage", "--version"])
HAS_NODE = check_installed(["node", "--version"])


@contextmanager
def pretext_view(*args: str) -> Generator:
    """Run `pretext view --no-launch` as a background process, yielding it
    to the caller, and terminate it on exit from the context."""
    process = subprocess.Popen(
        [PTX_CMD, "-v", "debug", "view", "--no-launch"] + list(args)
    )
    time.sleep(5)  # stall for possible build
    try:
        yield process
    finally:
        process.terminate()
        process.wait()


# ---------------------------------------------------------------------------
# 1. CLI basics
# ---------------------------------------------------------------------------


def test_entry_points(script_runner: ScriptRunner) -> None:
    """The CLI is reachable both as the `pretext` script and as
    `python -m pretext`."""
    ret = script_runner.run([PTX_CMD, "-v", "debug", "-h"])
    assert ret.success
    assert (
        subprocess.run(
            [PY_CMD, "-m", "pretext", "-v", "debug", "-h"], shell=True
        ).returncode
        == 0
    )


def test_version(script_runner: ScriptRunner) -> None:
    """`pretext --version` reports the package version."""
    ret = script_runner.run([PTX_CMD, "-v", "debug", "--version"])
    assert ret.stdout.strip() == pretext.VERSION


def test_devscript(script_runner: ScriptRunner) -> None:
    """`pretext devscript -h` aliases `python /path/to/core/pretext/pretext -h`,
    giving direct access to the core script for development."""
    result = script_runner.run([PTX_CMD, "devscript", "-h"])
    assert result.success
    assert "PreTeXt utility script" in result.stdout


def test_support(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext support` prints diagnostic information inside a project
    without erroring (used when reporting bugs)."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "-d", "."], cwd=tmp_path
    ).success
    assert script_runner.run([PTX_CMD, "support"], cwd=tmp_path).success


# ---------------------------------------------------------------------------
# 2. Project scaffolding: new / init / update-project
# ---------------------------------------------------------------------------


def test_new(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext new` scaffolds the default (book) project with all managed
    resource files -- except git-specific ones, since no repo exists yet."""
    assert script_runner.run([PTX_CMD, "-v", "debug", "new"], cwd=tmp_path).success
    # ensure sufficient permissions (n.b. 0oABC expresses integers in octal)
    assert (tmp_path / "new-pretext-project").stat().st_mode % 0o1000 >= 0o755
    for resource in constants.PROJECT_RESOURCES:
        if resource in constants.GIT_RESOURCES:
            assert not (
                tmp_path / "new-pretext-project" / constants.PROJECT_RESOURCES[resource]
            ).exists()
        else:
            assert (
                tmp_path / "new-pretext-project" / constants.PROJECT_RESOURCES[resource]
            ).exists()


@pytest.mark.parametrize("template", ["article", "course", "hello", "demo"])
def test_new_other_templates(
    template: str, tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext new TEMPLATE` scaffolds each of the alternative templates
    with a manifest and a source directory.  (The default book template is
    covered by test_new; slideshow gets built in test_slideshow.)"""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", template, "-d", "."], cwd=tmp_path
    ).success
    assert (tmp_path / "project.ptx").exists()
    assert (tmp_path / "source").is_dir()


def test_new_with_git(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """A freshly scaffolded project can be turned into a git repository."""
    assert script_runner.run([PTX_CMD, "-v", "debug", "new"], cwd=tmp_path).success
    # run git init in the new project directory
    script_runner.run(["git", "init"], cwd=tmp_path / "new-pretext-project")
    assert (tmp_path / "new-pretext-project" / ".git").exists()


def test_new_refuses_nested_project(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext new` inside an existing project refuses to nest a second
    project, exits nonzero, and creates nothing."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "-d", "."], cwd=tmp_path
    ).success
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "-d", "nested"], cwd=tmp_path
    )
    assert not result.success
    assert not (tmp_path / "nested").exists()


def test_init_and_update(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext init` in an empty directory creates the managed resource
    files (sans git ones), and `pretext update-project` restores any managed
    files that were deleted."""
    assert script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path).success
    for resource in constants.PROJECT_RESOURCES:
        if resource in constants.GIT_RESOURCES:
            assert not (tmp_path / constants.PROJECT_RESOURCES[resource]).exists()
        else:
            assert (tmp_path / constants.PROJECT_RESOURCES[resource]).exists()
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "update-project"], cwd=tmp_path
    ).success
    for resource in ["requirements.txt", "codechat_config.yaml"]:
        resource_path = tmp_path / constants.PROJECT_RESOURCES[resource]
        resource_path.unlink(missing_ok=True)
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "update-project"], cwd=tmp_path
    ).success
    for resource in constants.PROJECT_RESOURCES:
        if resource in constants.GIT_RESOURCES:
            assert not (tmp_path / constants.PROJECT_RESOURCES[resource]).exists()
        else:
            assert (tmp_path / constants.PROJECT_RESOURCES[resource]).exists()


def test_init_and_update_with_git(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """In a git repository, init/update also manage the git-specific
    resources; update-project leaves user-modified files alone but refreshes
    unmodified ones (like an old requirements.txt) to the current version."""
    script_runner.run(["git", "init"], cwd=tmp_path)
    script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path)
    for resource in constants.PROJECT_RESOURCES:
        assert (tmp_path / constants.PROJECT_RESOURCES[resource]).exists()
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "update-project"], cwd=tmp_path
    ).success
    # Remove resources
    for resource in ["requirements.txt", "codechat_config.yaml", ".gitignore"]:
        resource_path = tmp_path / constants.PROJECT_RESOURCES[resource]
        resource_path.unlink(missing_ok=True)
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "update-project"], cwd=tmp_path
    ).success
    for resource in constants.PROJECT_RESOURCES:
        assert (tmp_path / constants.PROJECT_RESOURCES[resource]).exists()
    # Ensure modified files don't get updated.
    with open(tmp_path / ".gitignore", "a") as f:
        f.write("\n# Added by test\n")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "update-project"], cwd=tmp_path
    ).success
    assert "Added by test" in (tmp_path / ".gitignore").read_text()
    # Ensure older version of requirements does get updated.
    requirements_path = tmp_path / "requirements.txt"
    with open(requirements_path, "r") as file:
        lines = file.readlines()
    with open(requirements_path, "w") as file:
        for line in lines:
            if "pretext" in line:
                file.write("pretext == 1.0.0\n")
            else:
                file.write(line)
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "update-project"], cwd=tmp_path
    ).success
    with open(requirements_path, "r") as file:
        lines = file.readlines()
        assert f"pretext == {pretext.VERSION}\n" in lines[1]


def test_init_warns_in_existing_project(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext init` in an already-initialized project warns and leaves the
    existing manifest untouched (users must opt in with --refresh/--file)."""
    assert script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path).success
    manifest = tmp_path / "project.ptx"
    manifest.write_text(manifest.read_text() + "<!-- user edit -->\n")
    result = script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path)
    assert result.success
    combined_output = result.stdout + result.stderr
    assert "already exists" in combined_output
    assert "user edit" in manifest.read_text()


def test_init_refresh_single_file(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext init --file RESOURCE` refreshes just that resource, backing
    up the existing copy as `*.bak`."""
    assert script_runner.run([PTX_CMD, "-v", "debug", "init"], cwd=tmp_path).success
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pretext == 1.0.0\n")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "init", "-f", "requirements.txt"], cwd=tmp_path
    ).success
    assert f"pretext == {pretext.VERSION}" in requirements.read_text()
    assert (tmp_path / "requirements.txt.bak").read_text() == "pretext == 1.0.0\n"


# ---------------------------------------------------------------------------
# 3. Build
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found.",
)
@pytest.mark.skipif(
    not HAS_SAGE,
    reason="Skipped since sage isn't found.",
)
@pytest.mark.skipif(
    not HAS_ASY,
    reason="Skipped since asy isn't found.",
)
@pytest.mark.skip(
    "Skipping build test for now; building a subset fails when the full build needs to be done to get the qrcode xml files."
)
def test_build(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """Full build of the demo template (including a subset build first), in a
    path containing spaces.  Currently skipped: a subset build fails before a
    full build has generated the qrcode xml files."""
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
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web"], cwd=project_path
    ).success
    web_path = project_path / "output" / "web"
    assert web_path.exists()
    # Temporarily disable:
    # mapping = json.load(open(web_path / ".mapping.json"))
    # print(mapping)
    # # This mapping will vary if the project structure produced by ``pretext new`` changes. Be sure to keep these in sync!
    # # The path separator varies by platform.
    # assert mapping == DEMO_MAPPING


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found.",
)
def test_build_latex_images(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """Building with `-q` skips latex-image generation; a plain build
    generates the missing SVG assets."""
    project_path = tmp_path / "latex-image"
    shutil.copytree(EXAMPLES_DIR / "projects" / "latex-image", project_path)
    svg = project_path / "generated-assets" / "latex-image" / "tikz-test.svg"

    # Build without generating assets: SVG should not be created
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web", "-q"],
        cwd=project_path,
    ).success
    assert not svg.exists()

    # Build with assets: SVG should be created
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web"],
        cwd=project_path,
    ).success
    assert svg.exists()


def test_build_no_manifest(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext build` still works when project.ptx has been deleted, by
    assuming a default project structure."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "-d", "."], cwd=tmp_path
    ).success
    os.remove(tmp_path / "project.ptx")
    assert (tmp_path / "project.ptx").exists() is False
    assert script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=tmp_path).success


def test_build_theme(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext build --theme` builds only the target's theme without
    performing a full build."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "-d", "."], cwd=tmp_path
    ).success
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "--theme"], cwd=tmp_path
    ).success


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found.",
)
def test_override_source(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """The manifest's source can be overridden either with `-i PATH` or by
    passing a source file as the build argument (standalone build); paths
    that don't exist fail the build."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "-d", "."], cwd=tmp_path
    ).success
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "-i", "source/main.ptx"], cwd=tmp_path
    ).success
    assert (
        script_runner.run([PTX_CMD, "build", "-i", "main.ptx"], cwd=tmp_path).success
        is False
    )
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "source/main.ptx"], cwd=tmp_path
    ).success
    assert (
        script_runner.run(
            [PTX_CMD, "-v", "debug", "build", "main.ptx"], cwd=tmp_path
        ).success
        is False
    )


def test_build_clean(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext build --clean` destroys the target's output directory before
    building, removing stale files from previous builds."""
    project_path = tmp_path / "simple"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "simple", project_path
    )
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web"], cwd=project_path
    ).success
    stale_file = project_path / "output" / "web" / "stale-leftover.html"
    stale_file.write_text("<html></html>")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web", "--clean"], cwd=project_path
    ).success
    assert not stale_file.exists()
    assert (project_path / "output" / "web" / "index.html").exists()


def test_build_unknown_target_fails(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """Building a target name that isn't in the manifest exits nonzero and
    hints at the available target names."""
    project_path = tmp_path / "simple"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "simple", project_path
    )
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "nosuchtarget"], cwd=project_path
    )
    assert result.returncode == 1
    combined_output = result.stdout + result.stderr
    assert "nosuchtarget" in combined_output
    # The error message should list the actual targets as alternatives.
    assert "web" in combined_output


def test_build_deploys(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext build --deploys` builds exactly the targets configured for
    deployment (in the elaborate example: `web` but not `print`)."""
    project_path = tmp_path / "elaborate"
    shutil.copytree(
        EXAMPLES_DIR / "projects" / "project_refactor" / "elaborate", project_path
    )
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "--deploys"], cwd=project_path
    ).success
    assert (project_path / "build" / "here" / "web" / "index.html").exists()
    assert not (project_path / "build" / "here" / "my-pdf").exists()


def test_custom_xsl(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """Targets with custom XSL build into their own output directories."""
    custom_path = tmp_path / "custom"
    shutil.copytree(EXAMPLES_DIR / "projects" / "custom-xsl", custom_path)
    assert script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=custom_path).success
    assert (custom_path / "output" / "test").exists()
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "test2"], cwd=custom_path
    ).success
    assert (custom_path / "output" / "test2").exists()


# Known upstream bug: core's `pretext-latex-common.xsl` `toc-level-override`
# template has no case for a `<slideshow>` root (its sibling in
# `publisher-variables.xsl` does), so any build of a `<slideshow>` document
# logs `PTX:ERROR: Table of Contents level ... not determined`, which the
# CLI treats as a build failure even though output is still produced. This
# affects every format, not just beamer. Remove these skips (and the
# `test_slideshow_beamer` failure-mode assertions) once that's fixed
# upstream by adding `<xsl:when test="$root/slideshow">0</xsl:when>` to
# `pretext-latex-common.xsl`, matching `publisher-variables.xsl`.
_SLIDESHOW_TOC_LEVEL_BUG = "Known bug: PTX:ERROR: Table of Contents level not determined for <slideshow> roots (pretext-latex-common.xsl toc-level-override)"


@pytest.mark.skip(reason=_SLIDESHOW_TOC_LEVEL_BUG)
def test_slideshow(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """The slideshow template scaffolds and builds a revealjs `slides`
    target."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "slideshow", "-d", "."], cwd=tmp_path
    ).success
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "slides"], cwd=tmp_path
    ).success
    assert (tmp_path / "output" / "slides" / "index.html").exists()


@pytest.mark.skip(reason=_SLIDESHOW_TOC_LEVEL_BUG)
@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found.",
)
def test_slideshow_beamer(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """The slideshow template's `beamer` target builds the same
    `<slideshow>` source as the revealjs `slides` target into a
    LaTeX/Beamer PDF."""
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "new", "slideshow", "-d", "."], cwd=tmp_path
    ).success
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "beamer"], cwd=tmp_path
    ).success
    assert (tmp_path / "output" / "beamer" / "slides.pdf").exists()


# ---------------------------------------------------------------------------
# 4. Asset generation (pretext generate, and build's -g/-q flags)
#
# Expected behaviors are documented in docs/asset-generation.md:
# - plain `build`: (re)generate only assets whose source changed
# - `build -q`: never generate assets
# - `build -g`: always regenerate assets
# - `build -g -q`: contradiction; warn and behave like a plain build
# ---------------------------------------------------------------------------


def test_build_no_generate(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """
    Test the behavior of `pretext build -q` (no generate) and -g -q together.

    Expected behaviors (per docs/asset-generation.md):
    - `pretext build -q`: no assets are generated, even if source has changed.
    - `pretext build -g -q`: warning issued; proceeds as if neither flag was set.
    """
    prefigure_path = tmp_path / "prefigure"
    shutil.copytree(EXAMPLES_DIR / "projects" / "prefigure", prefigure_path)

    prefigure_asset = prefigure_path / "generated-assets" / "prefigure" / "pftest.svg"

    # --- Test -q: build without generating any assets ---
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "-q"], cwd=prefigure_path
    )
    assert result.success
    assert (
        not prefigure_asset.exists()
    ), "Prefigure assets should NOT be generated when using -q (no-generate)"

    # --- Test -g -q together: warning issued, behaves like normal build ---
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "-g", "-q"], cwd=prefigure_path
    )
    assert result.success
    # The warning message about conflicting flags should appear in the output.
    combined_output = result.stdout + result.stderr
    assert (
        "doesn't make sense" in combined_output
    ), "A warning about using -g and -q together should be emitted"
    # Since the flags cancel each other, behavior is like a normal build.
    # On a clean project, that means the missing prefigure asset should be generated.
    assert (
        prefigure_asset.exists()
    ), "With -g and -q together, prefigure assets should be generated on a clean project (flags cancel each other)"


def test_build_force_generate_prefigure(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """
    Test the behavior of `pretext build -g` (force generate) and regular builds.

    Expected behaviors (per docs/asset-generation.md):
    - `pretext build -g`: all assets generated regardless of whether source has changed.
    - Regular `pretext build` after a successful build: assets NOT regenerated when source is unchanged.
    """
    prefigure_path = tmp_path / "prefigure"
    shutil.copytree(EXAMPLES_DIR / "projects" / "prefigure", prefigure_path)

    prefigure_asset = prefigure_path / "generated-assets" / "prefigure" / "pftest.svg"

    # --- Test -g: build with force-generate ---
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "-g"], cwd=prefigure_path
    )
    assert result.success
    assert (
        prefigure_asset.exists()
    ), "Prefigure asset should be generated when using -g (force generate)"
    assert (
        prefigure_path / "output" / "web"
    ).exists(), "Build output should exist after `pretext build -g`"

    # --- Test regular build does NOT regenerate when source is unchanged ---
    # Delete the generated asset to simulate a missing file after a previous build.
    prefigure_asset.unlink()
    assert not prefigure_asset.exists()

    # A regular build (no -g flag) should NOT regenerate since source hash has not changed.
    result = script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=prefigure_path)
    assert result.success
    assert (
        not prefigure_asset.exists()
    ), "Regular `pretext build` should NOT regenerate prefigure assets when source is unchanged"

    # --- Test -g regenerates even though source is unchanged ---
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "-g"], cwd=prefigure_path
    )
    assert result.success
    assert (
        prefigure_asset.exists()
    ), "`pretext build -g` should regenerate prefigure assets even when source is unchanged"


@pytest.mark.skipif(
    not HAS_ASY,
    reason="Skipped since asy isn't found.",
)
def test_build_force_generate_asymptote(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext build -g` regenerates asymptote assets using the local asy
    installation."""
    graphics_path = tmp_path / "graphics"
    shutil.copytree(EXAMPLES_DIR / "projects" / "graphics", graphics_path)

    asymptote_asset = graphics_path / "generated-assets" / "asymptote" / "test.html"

    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "-g"], cwd=graphics_path
    )
    assert result.success
    assert (
        asymptote_asset.exists()
    ), "Asymptote asset should be generated when using -g (force generate)"


def test_generate_graphics_prefigure(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext generate prefigure` produces prefigure SVG assets."""
    prefigure_path = tmp_path / "prefigure"
    shutil.copytree(EXAMPLES_DIR / "projects" / "prefigure", prefigure_path)

    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "prefigure"], cwd=prefigure_path
    ).success
    assert (prefigure_path / "generated-assets" / "prefigure" / "pftest.svg").exists()


@pytest.mark.skipif(
    not HAS_ASY,
    reason="Skipped since asy isn't found.",
)
def test_generate_graphics_asymptote_local(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext generate asymptote` works with a local asy install, both for
    all diagrams, for a single xml:id (-x), and for a specific target (-t)."""
    graphics_path = tmp_path / "graphics"
    shutil.copytree(EXAMPLES_DIR / "projects" / "graphics", graphics_path)

    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "asymptote"], cwd=graphics_path
    ).success
    assert (graphics_path / "generated-assets" / "asymptote" / "test.html").exists()
    os.remove(graphics_path / "generated-assets" / "asymptote" / "test.html")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "-x", "test"], cwd=graphics_path
    ).success
    assert (graphics_path / "generated-assets" / "asymptote" / "test.html").exists()
    os.remove(graphics_path / "generated-assets" / "asymptote" / "test.html")
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "asymptote", "-t", "web"],
        cwd=graphics_path,
    ).success


def test_generate_graphics_asymptote_server(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`pretext generate asymptote` also works without a local asy install,
    by delegating to the asymptote server (asy-method="server")."""
    graphics_path = tmp_path / "graphics"
    shutil.copytree(EXAMPLES_DIR / "projects" / "graphics", graphics_path)

    # Force server-backed asymptote generation so this test is independent of local asy.
    project_manifest = graphics_path / "project.ptx"
    project_manifest.write_text(
        project_manifest.read_text().replace(
            '<project ptx-version="2">',
            '<project ptx-version="2" asy-method="server">',
        )
    )

    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "asymptote"], cwd=graphics_path
    ).success
    assert (graphics_path / "generated-assets" / "asymptote" / "test.html").exists()


def test_generate_datafile(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext generate datafile` converts data files (e.g. csv) into the
    xml representation used at build time."""
    datafile_path = tmp_path / "datafile"
    shutil.copytree(EXAMPLES_DIR / "projects" / "datafile", datafile_path)
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "datafile"], cwd=datafile_path
    ).success
    assert (datafile_path / "generated-assets" / "datafile" / "data-csv.xml").exists()


def test_generate_interactive(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext generate -t pdf` produces playwright-captured previews and
    qrcodes for interactive elements (needed by non-html formats)."""
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


def test_custom_webwork_server(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext generate webwork` respects a custom webwork server configured
    in the manifest, and the project still builds afterwards."""
    custom_path = tmp_path / "custom"
    shutil.copytree(EXAMPLES_DIR / "projects" / "custom-wwserver", custom_path)
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "generate", "webwork"], cwd=custom_path
    )
    assert result.success
    assert "webwork.runestone.academy" in result.stdout
    result = script_runner.run([PTX_CMD, "-v", "debug", "build"], cwd=custom_path)
    assert result.success


@pytest.mark.skipif(
    not HAS_NODE,
    reason="Skipped since node isn't found (needed to extract dynamic substitutions).",
)
def test_build_webwork_and_dynamic_fillin(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """A project mixing a WeBWorK exercise with a dynamic (randomized)
    fill-in-the-blank exercise builds successfully.  The build must generate
    both the webwork asset (a rendered PG problem, fetched from a webwork
    server) and the dynamic-subs asset (the substitution file `pretext`
    extracts via node so that a static rendering shows one consistent, if
    randomized, version of the question)."""
    project_path = tmp_path / "dynamic-fillin"
    shutil.copytree(EXAMPLES_DIR / "projects" / "dynamic-fillin", project_path)
    result = script_runner.run(
        [PTX_CMD, "-v", "debug", "build", "web"], cwd=project_path
    )
    assert result.success

    assert (
        project_path / "generated-assets" / "webwork" / "exercise-webwork.xml"
    ).exists()

    subs_file = (
        project_path / "generated-assets" / "dynamic_subs" / "dynamic_substitutions.xml"
    )
    assert subs_file.exists()
    assert 'id="exercise-dynamic-fillin"' in subs_file.read_text()

    output_dir = project_path / "output" / "web"
    combined_html = "\n".join(p.read_text() for p in output_dir.glob("*.html"))
    assert 'id="exercise-webwork"' in combined_html
    assert 'id="rs-exercise-dynamic-fillin"' in combined_html
    assert 'data-component="fillintheblank"' in combined_html


# ---------------------------------------------------------------------------
# 5. Validate
#
# `pretext validate` runs core's `validate`, which writes a consolidated report
# (jing's schema messages plus the "validation-plus" stylesheet's) into `logs/`.
# Exit code contract (see the validate command's docstring in pretext/cli.py):
# 0 = valid, 1 = invalid or malformed, 2 = validation could not be performed.
# ---------------------------------------------------------------------------


def _validator_available() -> bool:
    """True if jing can run: it is the only engine, since lxml cannot compile
    the PreTeXt schema (it incorporates PreFigure's)."""
    return utils._jing_command() is not None


def _make_project(tmp_path: Path, script_runner: ScriptRunner) -> Path:
    """Scaffold a default project and return its root directory."""
    assert script_runner.run([PTX_CMD, "new"], cwd=tmp_path).success
    return tmp_path / "new-pretext-project"


@pytest.mark.skipif(not _validator_available(), reason="jing is not available")
def test_validate_invalid_source_is_nonzero(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """Well-formed but schema-invalid source makes `pretext validate` exit 1."""
    project = _make_project(tmp_path, script_runner)
    main_src = project / "source" / "main.ptx"
    main_src.write_text(
        '<?xml version="1.0"?>\n<pretext><article><section>Text outside of element.</section></article></pretext>\n'
    )
    ret = script_runner.run([PTX_CMD, "validate"], cwd=project)
    assert ret.returncode == 1


def test_validate_malformed_xml_is_nonzero(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """Source that isn't even well-formed XML makes `pretext validate` exit 1
    (before any schema validation is attempted)."""
    project = _make_project(tmp_path, script_runner)
    main_src = project / "source" / "main.ptx"
    main_src.write_text("<pretext>\n")  # not well-formed
    ret = script_runner.run([PTX_CMD, "validate"], cwd=project)
    assert ret.returncode == 1


@pytest.mark.skipif(not _validator_available(), reason="jing is not available")
def test_validate_dev_schema_runs(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext validate --dev` validates against the dev schema; a fresh
    template project passes."""
    project = _make_project(tmp_path, script_runner)
    ret = script_runner.run([PTX_CMD, "validate", "--dev"], cwd=project)
    assert ret.returncode == 0


def test_validate_could_not_validate_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script_runner: ScriptRunner
) -> None:
    """With no jing to run, `pretext validate` exits 2 to distinguish
    "could not check" from "invalid"."""
    from click.testing import CliRunner
    from pretext import cli
    from pretext import utils as putils
    from pretext.core import common as core_common

    project = _make_project(tmp_path, script_runner)
    monkeypatch.chdir(project)
    # Avoid the network update check, and make jing (and only jing) unavailable,
    # as core sees it.
    monkeypatch.setattr(putils, "check_for_updates", lambda *a, **k: None)
    real_get_executable_cmd = core_common.get_executable_cmd

    def _no_jing(exec_name: str) -> List[str]:
        if exec_name == "jing":
            raise OSError("cannot locate executable with configuration name `jing`")
        return real_get_executable_cmd(exec_name)

    monkeypatch.setattr(core_common, "get_executable_cmd", _no_jing)
    result = CliRunner().invoke(cli.main, ["validate"])
    assert result.exit_code == 2


def test_validate_engine_salve_unavailable_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script_runner: ScriptRunner
) -> None:
    """Asking for the salve engine when it can't be set up exits 2, rather than
    silently validating with jing and reporting on the wrong engine."""
    from click.testing import CliRunner
    from pretext import cli
    from pretext import utils as putils

    project = _make_project(tmp_path, script_runner)
    monkeypatch.chdir(project)
    monkeypatch.setattr(putils, "check_for_updates", lambda *a, **k: None)
    monkeypatch.setattr(putils, "salve_shim_command", lambda: None)
    result = CliRunner().invoke(cli.main, ["validate", "--engine", "salve"])
    assert result.exit_code == 2


@pytest.mark.skipif(
    not (resources.resource_base_path() / "salve" / "node_modules").exists(),
    reason="the salve engine has not been installed (run `pretext validate --engine salve` once)",
)
def test_validate_engine_salve_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script_runner: ScriptRunner
) -> None:
    """A template project validates cleanly through the salve engine too. Skipped
    until a developer has installed it, since first use needs npm and a network."""
    from click.testing import CliRunner
    from pretext import cli
    from pretext import utils as putils

    project = _make_project(tmp_path, script_runner)
    monkeypatch.chdir(project)
    monkeypatch.setattr(putils, "check_for_updates", lambda *a, **k: None)
    # `cli.error_flush_handler` is a module global, so errors logged by an
    # earlier in-process invocation would make this run exit 1 on their account.
    # A real run is a fresh process; here the buffer has to be emptied by hand.
    cli.error_flush_handler.buffer.clear()
    result = CliRunner().invoke(cli.main, ["validate", "--engine", "salve"])
    assert result.exit_code == 0
    assert (project / "logs" / "main-validation.txt").exists()


@pytest.mark.skipif(not _validator_available(), reason="jing is not available")
def test_validate_terse_method_is_machine_readable(
    tmp_path: Path, script_runner: ScriptRunner
) -> None:
    """`--method terse` writes core's tab-separated report: one message per
    line, each naming the source file it came from."""
    project = _make_project(tmp_path, script_runner)
    main_src = project / "source" / "main.ptx"
    main_src.write_text(
        '<?xml version="1.0"?>\n<pretext><article><section>Text outside of element.</section></article></pretext>\n'
    )
    ret = script_runner.run([PTX_CMD, "validate", "--method", "terse"], cwd=project)
    assert ret.returncode == 1
    report = (project / "logs" / "main-validation.txt").read_text()
    lines = [line for line in report.splitlines() if line.strip()]
    assert len(lines) > 0
    for line in lines:
        fields = line.split("\t")
        assert len(fields) == 5
        assert fields[0] == "main.ptx"


# ---------------------------------------------------------------------------
# 6. View (preview server)
# ---------------------------------------------------------------------------


def test_view(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext view` starts an HTTP server for the built project, records it
    in the server registry, serves the output, and `view -s` stops it."""
    os.chdir(tmp_path)
    assert script_runner.run([PTX_CMD, "-v", "debug", "new", "-d", "1"]).success
    os.chdir(Path("1"))
    assert script_runner.run([PTX_CMD, "-v", "debug", "build"]).success
    port = random.randint(10_000, 65_535)
    with pretext_view("-p", f"{port}"):
        project_hash = utils.hash_path(Path.cwd().resolve())
        running_server = None
        for _ in range(50):
            running_server = server.active_server_for_path_hash(project_hash)
            if running_server is not None and running_server.is_active_server():
                break
            time.sleep(0.1)
        assert running_server is not None
        r = requests.get(f"http://localhost:{running_server.port}")
        assert r.status_code == 200
        assert script_runner.run([PTX_CMD, "-v", "debug", "view", "-s"]).success


# ---------------------------------------------------------------------------
# 7. Deploy
# ---------------------------------------------------------------------------


def test_deploy(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext deploy --stage-only` stages the deploy-configured targets and
    the project's landing page without pushing anywhere.  (An actual deploy
    requires a configured GitHub remote, so it isn't exercised here; the
    staging logic itself is covered in more depth by
    test_project.py::test_stage.)"""
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


# ---------------------------------------------------------------------------
# 8. Import (LaTeX conversion, experimental)
# ---------------------------------------------------------------------------


def test_import_latex(tmp_path: Path, script_runner: ScriptRunner) -> None:
    """`pretext import FILE.tex` converts a LaTeX document to PreTeXt source
    via plastex, producing main.ptx plus one file per sectioning unit."""
    (tmp_path / "sample.tex").write_text(
        "\\documentclass{article}\n"
        "\\title{Imported Document}\n"
        "\\begin{document}\n"
        "\\section{First Section}\n"
        "Some text with math $x^2 + y^2 = z^2$.\n"
        "\\end{document}\n"
    )
    assert script_runner.run(
        [PTX_CMD, "-v", "debug", "import", "sample.tex", "-o", "converted"],
        cwd=tmp_path,
    ).success
    assert (tmp_path / "converted" / "main.ptx").exists()
    # The section should have been split into its own source file.
    section_files = list((tmp_path / "converted").glob("section-*.ptx"))
    assert len(section_files) == 1
