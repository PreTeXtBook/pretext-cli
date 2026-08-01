"""
Tests of the `pretext.project` Python API: the `Project` and `Target`
models parsed from ``project.ptx`` manifests, and their build/deploy
behavior.

These tests drive the library directly (no CLI subprocess), using the
example projects in ``tests/examples/projects``:

- ``project_refactor/simple``     -- minimal v2 manifest (web/print/runestone)
- ``project_refactor/elaborate``  -- v2 manifest exercising every attribute
- ``project_refactor/legacy``     -- v1 (legacy) manifest
- ``project_refactor/assets``     -- targets for asset-table comparison
- others (``xref``, ``xi_pub``, ...) for specific behaviors

The CLI equivalents of these behaviors are tested in ``test_cli.py``.
"""

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


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Note: several tests are skipped, since xelatex wasn't installed.",
)
def test_note_if_no_xelatex() -> None:
    """Not a real test: shows up as a *skip* in the report when xelatex is
    missing, alerting the developer that pdf assertions are being skipped."""
    pass


def test_defaults(tmp_path: Path) -> None:
    """A Project created programmatically (no manifest) uses the documented
    default paths, and its targets default to the bundled publication file,
    xelatex pdf generation, and local asymptote generation."""
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
            assert target.pdf_method == pr.PdfMethod.XELATEX
            assert target.stringparams == {}
    # Default asy_method should be "local"
    assert project.asy_method == pr.AsyMethod.LOCAL
    for t in ts:
        name, _ = t
        assert project.get_target(name).asy_method == pr.AsyMethod.LOCAL


def test_serve(tmp_path: Path) -> None:
    """Project.server_process() serves the output directory over HTTP,
    returning 404 before content exists and 200 after."""
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
    """Parsing the simple v2 manifest yields its three targets with correct
    formats/platforms, and unspecified settings fall back to the defaults."""
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
        ) == Path("output/rs")

        assert not project.has_target("foo")

        # When asy-method is not specified, the default should be "local"
        assert project.asy_method == pr.AsyMethod.LOCAL
        assert t_web.asy_method == pr.AsyMethod.LOCAL
        assert t_print.asy_method == pr.AsyMethod.LOCAL

        default_project = pr.Project(ptx_version="2")
        assert default_project.site == project.site
        assert default_project.output_dir == project.output_dir
        assert default_project._path == project._path


def test_manifest_simple_build(tmp_path: Path) -> None:
    """Each target of the simple project builds into its own output
    directory: html (with a CodeChat .mapping.json), runestone (with its
    manifest), and pdf when xelatex is available."""
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        project.get_target("web").build()
        assert (prj_path / "output" / "web" / "index.html").exists()
        # html builds produce the source-to-output map used by CodeChat.
        mapping = json.loads(
            (prj_path / "output" / "web" / ".mapping.json").read_text()
        )
        assert mapping == {"source/main.ptx": ["article-id"]}
        project.get_target("rs").build()
        assert (prj_path / "output" / "rs" / "index.html").exists()
        assert (prj_path / "output" / "rs" / "runestone-manifest.xml").exists()
        if HAS_XELATEX:
            project.get_target("print").build()
            assert (prj_path / "output" / "print" / "main.pdf").exists()


def test_manifest_elaborate(tmp_path: Path) -> None:
    """Parsing the elaborate manifest picks up every customized project- and
    target-level attribute (paths, executables, stringparams, asy-method,
    deploy-dir, output-filename, custom xsl)."""
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
        # Deprecated executables still parse, but are never handed to core.
        assert project._executables.liblouis == "foobar"
        assert "liblouis" not in project._executables.model_dump()
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
        # assert sorted(t_web.server, key=lambda k: k.name) == [
        #    pr.Server(name="asy", url="http://example1.com"),  # type: ignore
        #    pr.Server(name="sage", url="http://example2.com"),  # type: ignore
        # ]

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
        # assert sorted(t_print.server, key=lambda k: k.name) == [
        #    pr.Server(name="asy", url="http://example3.com"),  # type: ignore
        #    pr.Server(name="sage", url="http://example2.com"),  # type: ignore
        # ]


def test_manifest_elaborate_build(tmp_path: Path) -> None:
    """The elaborate project builds into its customized output locations
    (nested output dir, custom pdf output filename)."""
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
    """A v1 (legacy) manifest is parsed into the modern model: targets,
    paths, pdf methods, stringparams, and executables all carry over."""
    prj_path = EXAMPLES_DIR / "projects" / "project_refactor" / "legacy"
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 3

        assert project._executables.xelatex == "xelatex"
        # Deprecated executables still parse, but are never handed to core.
        assert project._executables.liblouis == "foobar"
        assert "liblouis" not in project._executables.model_dump()
        # Executables the legacy format has no element for fall back to their
        # modern defaults, so core is never handed a short dict.
        assert project._executables.model_dump()["jing"] == "jing"
        assert project._executables.model_dump()["mermaid"] == "mmdc"

        t_html = project.get_target("html")
        assert t_html is not None
        assert t_html.format == "html"
        assert t_html.source_abspath() == project.abspath() / Path("source", "main.ptx")
        assert t_html.publication_abspath() == project.abspath() / Path(
            "publication", "publication.ptx"
        )
        assert t_html.output_dir_abspath() == project.abspath() / Path("output", "html")
        assert t_html.pdf_method == "xelatex"
        assert t_html.stringparams == {"one": "uno", "two": "dos"}

        t_latex = project.get_target("latex")
        assert t_latex.format == "latex"
        assert t_latex.source == Path("source", "main.ptx")
        assert t_latex.publication == Path("publication", "publication.ptx")
        assert t_latex.output_dir == Path("output", "latex")
        assert t_latex.pdf_method == "xelatex"

        t_pdf = project.get_target("pdf")
        assert t_pdf.format == "pdf"
        assert t_pdf.source == Path("source", "main.ptx")
        assert t_pdf.publication == Path("publication", "publication.ptx")
        assert t_pdf.output_dir == Path("output", "pdf")
        assert t_pdf.pdf_method == "pdflatex"

        assert not project.has_target("foo")

        assert project._executables.latex == "latex1"


def test_manifest_legacy_wrong() -> None:
    """Repeat of test_manifest_legacy with a manifest containing extra,
    unknown elements: legacy parsing ignores them instead of failing.
    (Contrast with v2 manifests, where extras raise -- see test_validation.)"""
    prj_path = EXAMPLES_DIR / "projects" / "project_refactor" / "legacy_extra"
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert len(project.targets) == 3

        assert project._executables.xelatex == "xelatex"
        # Deprecated executables still parse, but are never handed to core.
        assert project._executables.liblouis == "foobar"
        assert "liblouis" not in project._executables.model_dump()
        # Executables the legacy format has no element for fall back to their
        # modern defaults, so core is never handed a short dict.
        assert project._executables.model_dump()["jing"] == "jing"
        assert project._executables.model_dump()["mermaid"] == "mmdc"

        t_html = project.get_target("html")
        assert t_html is not None
        assert t_html.format == "html"
        assert t_html.source_abspath() == project.abspath() / Path("source", "main.ptx")
        assert t_html.publication_abspath() == project.abspath() / Path(
            "publication", "publication.ptx"
        )
        assert t_html.output_dir_abspath() == project.abspath() / Path("output", "html")
        assert t_html.pdf_method == "xelatex"
        assert t_html.stringparams == {"one": "uno", "two": "dos"}

        t_latex = project.get_target("latex")
        assert t_latex.format == "latex"
        assert t_latex.source == Path("source", "main.ptx")
        assert t_latex.publication == Path("publication", "publication.ptx")
        assert t_latex.output_dir == Path("output", "latex")
        assert t_latex.pdf_method == "xelatex"

        t_pdf = project.get_target("pdf")
        assert t_pdf.format == "pdf"
        assert t_pdf.source == Path("source", "main.ptx")
        assert t_pdf.publication == Path("publication", "publication.ptx")
        assert t_pdf.output_dir == Path("output", "pdf")
        assert t_pdf.pdf_method == "pdflatex"

        assert not project.has_target("foo")

        assert project._executables.latex == "latex1"


def test_executables_match_core() -> None:
    """The executables handed to core are exactly the keys the core script's
    `pretext.cfg` declares -- no missing key (core looks these up in a plain
    dict) and no vestigial extras."""
    assert set(pr.Executables().model_dump()) == {
        "latex",
        "pdflatex",
        "xelatex",
        "asy",
        "mermaid",
        "sage",
        "pdfeps",
        "node",
        "perl",
        "fop",
        "jing",
    }


def test_executables_jing_from_manifest(tmp_path: Path) -> None:
    """A `jing` in executables.ptx reaches core, so a user whose jing is off the
    search path (or is a `java -jar ...` command) can point the CLI at it."""
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    (prj_path / "executables.ptx").write_text(
        '<executables jing="java -jar /opt/jing.jar"/>'
    )
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        assert project._executables.jing == "java -jar /opt/jing.jar"
        # `model_dump()` is what `init_core()` hands to core, options and all.
        assert project._executables.model_dump()["jing"] == "java -jar /opt/jing.jar"


def test_validate_source_salve_engine_swaps_and_restores_jing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The salve engine reaches core by standing in for the `jing` executable,
    and the project's own executables are restored once validation is done (so
    a later build isn't left pointing at the shim)."""
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        target = project.get_target()

        handed_to_core = []
        monkeypatch.setattr(
            pr.utils, "salve_shim_command", lambda: ["node", "/x/shim.mjs"]
        )
        monkeypatch.setattr(
            pr.core, "set_executables", lambda d: handed_to_core.append(dict(d))
        )
        monkeypatch.setattr(pr.core, "validate", lambda **kwargs: None)

        target.validate_source(engine="salve")

        assert handed_to_core[0]["jing"] == "node /x/shim.mjs"
        assert handed_to_core[-1]["jing"] == "jing"


def test_validate_source_salve_unavailable_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no usable shim, validation reports that it could not run (exit 2 at
    the CLI) instead of falling back to jing and quietly testing the wrong thing."""
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()

        monkeypatch.setattr(pr.utils, "salve_shim_command", lambda: None)

        def _unreachable(**kwargs: object) -> None:
            raise AssertionError("core.validate should not be called")

        monkeypatch.setattr(pr.core, "validate", _unreachable)
        assert project.get_target().validate_source(engine="salve") is None


def test_executables_deprecated_and_unknown() -> None:
    """Executables core no longer uses are accepted (older `executables.ptx`
    files must keep parsing) but withheld from core; genuinely unknown ones
    are still rejected, so typos don't pass silently."""
    execs = pr.Executables(liblouis="file2brl", pdfsvg="pdf2svg", pdfpng="convert")
    assert "liblouis" not in execs.model_dump()
    assert "pdfsvg" not in execs.model_dump()
    assert "pdfpng" not in execs.model_dump()

    with pytest.raises(pydantic.ValidationError):
        pr.Executables(jjing="typo")  # type: ignore[call-arg]


def test_html_build_permissions(tmp_path: Path) -> None:
    """HTML output is world-readable (0o755+), so it can be served directly
    from a web root."""
    prj_path = tmp_path / "hello"
    shutil.copytree(TEMPLATES_DIR / "hello", prj_path)
    with utils.working_directory(prj_path):
        p = pr.Project(ptx_version="2")
        p.new_target("web", "html").build()
        assert (prj_path / "output" / "web").exists()
        assert (prj_path / "output" / "web").stat().st_mode % 0o1000 >= 0o755


@pytest.mark.skip(reason="Temporarily disabled")
def test_demo_html_build(tmp_path: Path) -> None:
    """Full html build of the demo template in a path with spaces, checking
    the CodeChat mapping of the multi-file source.  Currently skipped: the
    demo build requires sage/asy assets and is expensive; the mapping logic
    itself is unit-tested in test_codechat.py."""
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
    """Building with an xmlid produces output only for that subtree."""
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
    """An html target with zip compression produces a single zip file
    instead of a website directory."""
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


def test_xinclude_publication_build(tmp_path: Path) -> None:
    """A publication file assembled via xinclude is honored (here it sets a
    custom external assets directory), and the target still builds."""
    prj_path = tmp_path / "xi_pub"
    shutil.copytree(EXAMPLES_DIR / "projects" / "xi_pub", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        target = project.get_target("web")
        assert target.external_dir() == Path("../assets")
        target.build()
        assert (target.output_dir_abspath() / "index.html").exists()


def test_asset_table(tmp_path: Path) -> None:
    """Asset tables (hashes of asset source, used to decide what needs
    regenerating) are equal exactly when two targets share asset-relevant
    settings."""
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
    """The deploy/deploy-dir attribute permutations determine to_deploy()
    and the deploy directory name; then a staged deployment of the elaborate
    project lands its deployable target plus the static site landing page."""
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


def test_deploy_path(tmp_path: Path) -> None:
    """deploy_path() links to the built file for single-file formats
    (pdf/epub) when one can be found, and to the deploy directory otherwise;
    an explicit output_filename always wins."""
    prj_path = tmp_path / "test_deploy_path"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    (prj_path / "project.ptx").unlink()
    with utils.working_directory(prj_path):
        project = pr.Project(ptx_version="2")

        # For PDF target with no output_filename and no output dir: fallback to directory
        t_pdf = project.new_target(name="print", format="pdf", deploy_dir="print-dir")
        assert t_pdf.deploy_path() == Path("print-dir")

        # Simulate a built PDF in the output directory
        pdf_output_dir = t_pdf.output_dir_abspath()
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        (pdf_output_dir / "main.pdf").touch()

        # deploy_path() should now find the PDF and include it in the path
        assert t_pdf.deploy_path() == Path("print-dir") / "main.pdf"

        # If output_filename is explicitly set, it should take precedence
        t_pdf_explicit = project.new_target(
            name="print-explicit",
            format="pdf",
            deploy_dir="print-dir2",
            output_filename="custom.pdf",
        )
        assert t_pdf_explicit.deploy_path() == Path("print-dir2") / "custom.pdf"

        # For HTML format (directory output), deploy_path() should still return the directory
        t_html = project.new_target(name="web", format="html", deploy_dir="web-dir")
        assert t_html.deploy_path() == Path("web-dir")

        # EPUB target with no output file: fallback to directory
        t_epub = project.new_target(name="epub", format="epub", deploy_dir="epub-dir")
        assert t_epub.deploy_path() == Path("epub-dir")

        # Simulate a built EPUB
        epub_output_dir = t_epub.output_dir_abspath()
        epub_output_dir.mkdir(parents=True, exist_ok=True)
        (epub_output_dir / "book.epub").touch()

        assert t_epub.deploy_path() == Path("epub-dir") / "book.epub"


def test_validation(tmp_path: Path) -> None:
    """Invalid target configurations (duplicate server names, output options
    that conflict with the format/platform, unknown attributes or elements)
    raise pydantic ValidationErrors instead of being silently accepted."""
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


def test_latex_build(tmp_path: Path) -> None:
    """A latex-format target builds a .tex file (no LaTeX engine needed,
    unlike the pdf format)."""
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        target = project.new_target("tex", "latex")
        target.build()
        assert (prj_path / "output" / "tex" / "main.tex").exists()


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found (needed for the epub cover).",
)
def test_epub_build(tmp_path: Path) -> None:
    """An epub-format target builds a single .epub file."""
    prj_path = tmp_path / "simple"
    shutil.copytree(EXAMPLES_DIR / "core" / "examples" / "epub", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project(ptx_version="2", source=Path(""), publication=Path(""))
        target = project.new_target(
            "ebook",
            "epub",
            source=Path("epub-sampler.xml"),
            publication=Path("publication.xml"),
        )
        target.build()
        assert (prj_path / "output" / "ebook" / "epub-sampler.epub").exists()


@pytest.mark.skipif(
    not HAS_XELATEX,
    reason="Skipped since xelatex isn't found.",
)
@pytest.mark.skip(reason="Temporarily disabled until docker image gets beamer.cls")
def test_beamer_build(tmp_path: Path) -> None:
    """A beamer-format target converts a `<slideshow>` source (the
    slideshow template's `beamer` target) into a LaTeX/Beamer PDF, using
    the same source as the revealjs `slides` target.

    Unlike the CLI (see the skipped `test_slideshow_beamer` in
    `test_cli.py`), calling `Target.build()` directly does not raise just
    because the build logged an error, so this passes even though core
    currently logs a `PTX:ERROR: Table of Contents level ... not
    determined` for `<slideshow>` roots (a known gap in
    `pretext-latex-common.xsl`; see the comment above `test_slideshow` in
    `test_cli.py`).
    """
    prj_path = tmp_path / "slideshow"
    shutil.copytree(TEMPLATES_DIR / "slideshow", prj_path)
    with utils.working_directory(prj_path):
        project = pr.Project.parse()
        target = project.get_target("beamer")
        assert target.format == "beamer"
        target.build()
        assert (prj_path / "output" / "beamer" / "slides.pdf").exists()


def test_no_knowls(tmp_path: Path) -> None:
    """Building with no_knowls=True replaces knowled cross-references with
    plain hyperlinks (used when previewing individual sections)."""
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


def test_stage(tmp_path: Path) -> None:
    """stage_deployment() picks the right strategy as the project changes:
    a lone default target stages directly; marking targets deployable adds a
    pelican-generated landing page; a site/ directory switches to static;
    and a site.ptx there switches to a pelican_custom site."""
    prj_path = tmp_path / "test_stage"
    shutil.copytree(EXAMPLES_DIR / "projects" / "project_refactor" / "simple", prj_path)
    (prj_path / "project.ptx").unlink()
    with utils.working_directory(prj_path):
        project = pr.Project(ptx_version="2")

        project.new_target(name="web", format="html").build()
        project.new_target(name="web2", format="html").build()
        project.new_target(name="web3", format="html").build()

        assert project.deploy_strategy() == "default_target"
        project.stage_deployment()
        assert project.stage_abspath().exists()
        assert (project.stage_abspath() / "article-id.html").exists()
        shutil.rmtree(project.stage_abspath())

        project.get_target(name="web2").deploy = "yes"
        assert project.deploy_strategy() == "pelican_default"
        project.stage_deployment()
        assert project.stage_abspath().exists()
        assert (project.stage_abspath() / "index.html").exists()
        assert (project.stage_abspath() / "web2" / "article-id.html").exists()
        shutil.rmtree(project.stage_abspath())

        project.site_abspath().mkdir()
        (project.site_abspath() / "foo.html").touch()
        assert project.deploy_strategy() == "static"
        project.stage_deployment()
        assert project.stage_abspath().exists()
        assert (project.stage_abspath() / "foo.html").exists()
        assert (project.stage_abspath() / "web2" / "article-id.html").exists()
        shutil.rmtree(project.stage_abspath())

        (project.site_abspath() / "site.ptx").touch()
        with open(project.site_abspath() / "site.ptx", "w") as f:
            print(
                "<site><ptx-site-description>foobar</ptx-site-description></site>",
                file=f,
            )
        assert project.deploy_strategy() == "pelican_custom"
        project.stage_deployment()
        assert project.stage_abspath().exists()
        assert (project.stage_abspath() / "index.html").exists()
        with open(project.stage_abspath() / "index.html", "r") as f:
            assert "foobar" in f.read()
        assert (project.stage_abspath() / "web2" / "article-id.html").exists()
        shutil.rmtree(project.stage_abspath())
