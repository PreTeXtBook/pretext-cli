import typing as t
import multiprocessing
import shutil
import tempfile
from pathlib import Path
from lxml import etree as ET
from . import core
from . import utils
from . import build as builder


class Project:
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, and Paths for where to build output and stage deployments.
    """

    def __init__(
        self,
        path: t.Optional[Path | str] = None,
        source: t.Optional[Path | str] = None,
        publication: t.Optional[Path | str] = None,
        output: t.Optional[Path | str] = None,
        deploy: t.Optional[Path | str] = None,
        xsl: t.Optional[Path | str] = None,
    ):
        self._targets: list[Target] = []
        self.path = path
        self.source = source
        self.publication = publication
        self.output = output
        self.deploy = deploy
        self.xsl = xsl

    @classmethod
    def parse(
        cls,
        path: Path | str = Path(),
        element: t.Optional[ET._Element] = None,
    ) -> "Project":
        p = Path(path)
        if element is None:
            if p.is_file():
                file_path = p
                dir_path = p.parent
            else:
                file_path = p / "project.ptx"
                dir_path = p
            element = ET.parse(file_path).getroot()
        if element.get("version") != "2":
            raise ValueError("project manifest is not version 2")
        project = cls(
            path=dir_path,
            source=element.get("source"),
            publication=element.get("publication"),
            output=element.get("output"),
            deploy=element.get("deploy"),
            xsl=element.get("xsl"),
        )
        for t in element.findall("./targets/target"):
            project.parse_target(t)
        return project

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._path = Path()
        else:
            self._path = Path(p)

    @property
    def source(self) -> Path:
        return self._source

    @source.setter
    def source(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._source = Path("source")
        else:
            self._source = Path(p)

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._publication = Path("publication")
        else:
            self._publication = Path(p)

    @property
    def output(self) -> Path:
        return self._output

    @output.setter
    def output(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._output = Path("output")
        else:
            self._output = Path(p)

    @property
    def deploy(self) -> Path:
        return self._deploy

    @deploy.setter
    def deploy(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._deploy = Path("deploy")
        else:
            self._deploy = Path(p)

    @property
    def xsl(self) -> Path:
        return self._xsl

    @xsl.setter
    def xsl(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._xsl = Path("xsl")
        else:
            self._xsl = Path(p)

    @property
    def targets(self) -> list["Target"]:
        return self._targets

    def parse_target(self, element: ET._Element) -> None:
        self._targets.append(Target.parse(self, element))

    def add_target(self, *args, **kwargs) -> None:
        self._targets.append(Target(self, *args, **kwargs))

    def target(self, name: t.Optional[str] = None) -> t.Optional["Target"]:
        """
        Attempts to return a target matching `name`.
        If `name` isn't provided, returns the default (first) target.
        """
        if len(self._targets) == 0:
            # no target to return
            return None
        if name is None:
            # return default target
            return self._targets[0]
        try:
            # return first target matching the provided name
            return next(t for t in self._targets if t.name == name)
        except StopIteration:
            # but no such target was found
            return None

    def abspath(self) -> Path:
        return self.path.resolve()

    def source_abspath(self) -> Path:
        return self.abspath() / self.source

    def publication_abspath(self) -> Path:
        return self.abspath() / self.publication

    def output_abspath(self) -> Path:
        return self.abspath() / self.output

    def server_process(
        self,
        mode: t.Literal["output", "deploy"] = "output",
        access: t.Literal["public", "private"] = "private",
        port: int = 8000,
        launch: bool = True,
    ) -> multiprocessing.Process:
        """
        Returns a process for running a simple local web server
        providing either the contents of `output` or `deploy`
        """
        if mode == "output":
            directory = self.output
        else:  # "deploy"
            directory = self.deploy

        return utils.server_process(directory, access, port, launch=launch)


class Target:
    """
    Representation of a target for a PreTeXt project: a specific
    build targeting a format such as HTML, LaTeX, etc.
    """

    # List of valid formats for a target.
    Format = t.Literal[
        "html",
        "latex",
        "pdf",
        "epub",
        "kindle",
        "braille",
        "webwork",
        "custom",
    ]

    # List of valid latex engines for a target.
    LatexEngine = t.Literal["xelatex", "latex", "pdflatex"]

    def __init__(
        self,
        project: Project,
        name: str,
        format: Format,
        source: t.Optional[Path | str] = None,
        publication: t.Optional[Path | str] = None,
        output: t.Optional[Path | str] = None,
        deploy: t.Optional[Path | str] = None,
        xsl: t.Optional[Path | str] = None,
        latex_engine: t.Optional[LatexEngine] = None,
        stringparams: dict[str, str] = {},
    ):
        """
        Construction of a new Target. Requires both a
        `name` and `format`.
        """
        self._project = project
        self.name = name
        self.format = format
        self.source = source
        self.publication = publication
        self.output = output
        self.deploy = deploy
        self.xsl = xsl
        self.latex_engine = latex_engine
        self.stringparams = stringparams

    @classmethod
    def parse(
        cls,
        project: Project,
        element: ET._Element,
    ) -> "Target":
        latex_engine = element.get("latex-engine")
        if latex_engine is not None:
            latex_engine = latex_engine.lower()
        stringparams = {}
        for param in element.findall("stringparam"):
            if param.get("key") is None or param.get("value") is None:
                raise ValueError("stringparam must have a key and value")
            stringparams[param.get("key")] = param.get("value")
        return cls(
            project,
            element.get("name"),
            element.get("format").lower(),
            source=element.get("source"),
            publication=element.get("publication"),
            output=element.get("output"),
            deploy=element.get("deploy"),
            xsl=element.get("xsl"),
            latex_engine=latex_engine,
            stringparams=stringparams,
        )

    @property
    def project(self) -> Project:
        return self._project

    @property
    def source(self) -> Path:
        return self._source

    @source.setter
    def source(self, path: t.Optional[Path | str]) -> None:
        if path is None:
            self._source = Path("main.ptx")
        else:
            self._source = Path(path)

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, path: t.Optional[Path | str]) -> None:
        if path is None:
            self._publication = Path("publication.ptx")
        else:
            self._publication = Path(path)

    @property
    def output(self) -> Path:
        return self._output

    @output.setter
    def output(self, path: t.Optional[Path | str]) -> None:
        if path is None:
            self._output = Path(self.name)
        else:
            self._output = Path(path)

    @property
    def deploy(self) -> Path:
        return self._deploy

    @deploy.setter
    def deploy(self, path: t.Optional[Path | str]) -> None:
        if path is None:
            self._deploy = None
        else:
            self._deploy = Path(path)

    @property
    def xsl(self) -> t.Optional[Path]:
        return self._xsl

    @xsl.setter
    def xsl(self, p: t.Optional[Path | str]) -> None:
        if p is None:
            self._xsl = None
        else:
            self._xsl = Path(p)

    @property
    def latex_engine(self) -> LatexEngine:
        return self._latex_engine

    @latex_engine.setter
    def latex_engine(self, engine: t.Optional[LatexEngine]) -> None:
        if engine is None:
            self._latex_engine = "xelatex"
        else:
            self._latex_engine = engine

    def source_abspath(self) -> Path:
        return self.project.source_abspath() / self.source

    def publication_abspath(self) -> Path:
        return self.project.publication_abspath() / self.publication

    def output_abspath(self) -> Path:
        return self.project.output_abspath() / self.output

    def external_dir(self) -> Path:
        return Path(
            ET.parse(self.publication_abspath())
            .find("./source/directories")
            .get("external")
        )

    def external_dir_abspath(self) -> Path:
        return (self.source_abspath().parent / self.external_dir()).resolve()

    def generated_dir(self) -> Path:
        return Path(
            ET.parse(self.publication_abspath())
            .find("./source/directories")
            .get("generated")
        )

    def generated_dir_abspath(self) -> Path:
        return (self.source_abspath().parent / self.generated_dir()).resolve()

    def ensure_asset_directories(self) -> None:
        self.external_dir_abspath().mkdir(parents=True, exist_ok=True)
        self.generated_dir_abspath().mkdir(parents=True, exist_ok=True)

    def clean_output(self, log_warning: t.Callable = print) -> None:
        # refuse to clean if output is not a subdirectory of the project or contains source/publication
        if self.project.abspath() not in self.output_abspath().parents:
            log_warning(
                "Refusing to clean output directory that isn't a proper subdirectory of the project."
            )
        # handle request to clean directory that does not exist
        elif not self.output_abspath().exists():
            log_warning(
                f"Directory {self.output_abspath()} already does not exist, nothing to clean."
            )
        # destroy the output directory
        else:
            log_warning(
                f"Destroying directory {self.output_abspath()} to clean previously built files."
            )
            shutil.rmtree(self.output_abspath())

    def build(
        self,
        clean: bool = False,
        xmlid_root: t.Optional[str] = None,
        log_info: t.Callable = print,
        log_warning: t.Callable = print,
    ) -> None:
        # Check for xml syntax errors and quit if xml invalid:
        if not utils.xml_syntax_is_valid(self.source_abspath()):
            raise RuntimeError("XML syntax for source file is invalid")
        if not utils.xml_syntax_is_valid(self.publication_abspath(), "publication"):
            raise RuntimeError("XML syntax for publication file is invalid")
        # Validate xml against schema; continue with warning if invalid:
        if not utils.xml_source_validates_against_schema(self.source_abspath()):
            raise RuntimeError("XML in source file does not validate with schema")

        # Clean output upon request
        if clean:
            self.clean_output()

        # Ensure the asset directories exist.
        self.ensure_asset_directories()

        with tempfile.TemporaryDirectory() as temp_xsl_path:
            # if custom xsl, copy it into a temporary directory (different from the building temporary directory)
            if (txp := self.xsl) is not None:
                log_info(f"Building with custom xsl {txp}")
                utils.copy_custom_xsl(txp, temp_xsl_path)
                custom_xsl = temp_xsl_path / txp.name
            else:
                custom_xsl = None

            # warn if "publisher" is one of the string-param keys:
            if "publisher" in self.stringparams:
                log_warning(
                    "You specified a publication file via a stringparam. "
                    + "This is ignored in favor of the publication file given by the "
                    + "<publication> element in the project manifest."
                )

            log_info(f"Preparing to build into {self.output_abspath()}.")

            try:
                if self.format == "html":
                    builder.html(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                        xmlid_root,
                        False,
                    )
                elif self.format == "html-zip":
                    builder.html(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                        xmlid_root,
                        True,
                    )
                elif self.format == "latex":
                    builder.latex(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                    )
                    # TODO
                    # # core script doesn't put a copy of images in output for latex builds, so we do it instead here
                    # shutil.copytree(
                    #     target.external_dir_found(),
                    #     target.output_dir() / "external",
                    #     dirs_exist_ok=True,
                    # )
                    # shutil.copytree(
                    #     target.generated_dir_found(),
                    #     target.output_dir() / "generated",
                    #     dirs_exist_ok=True,
                    # )
                elif self.format == "pdf":
                    builder.pdf(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                        self.latex_engine,
                    )
                # elif self.format == "custom":
                #     if custom_xsl is None:
                #         raise RuntimeError("Must specify custom XSL for custom build.")
                #     builder.custom(
                #         target.source(),
                #         target.publication(),
                #         target.output_dir(),
                #         target.stringparams(),
                #         custom_xsl,
                #         target.output_filename(),
                #     )
                elif self.format == "epub":
                    builder.epub(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                    )
                elif self.format == "kindle":
                    builder.kindle(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                    )
                elif self.format in ("braille", "braille-emboss"):
                    builder.braille(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        page_format="emboss",
                    )
                elif self.format == "braille-electronic":
                    builder.braille(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        page_format="electronic",
                    )
                elif self.format == "webwork-sets":
                    builder.webwork_sets(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        False,
                    )
                elif self.format == "webwork-sets-zip":
                    builder.webwork_sets(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        True,
                    )
                else:
                    raise NotImplementedError(
                        f"Building {self.format} is not yet supported."
                    )
            except Exception as e:
                pass  # TODO handle in CLI
                # log.critical(
                #     f"A fatal error has occurred:\n {e} \nFor more info, run pretext with `-v debug`"
                # )
                # log.debug("Exception info:\n##################\n", exc_info=True)
                # log_info("##################")
                # sys.exit(f"Failed to build pretext target {target.format()}.  Exiting...")
            finally:
                # remove temp directories left by core.
                core.release_temporary_directories()
        # build was successful
        log_info(f"\nSuccess! Run `pretext view` to see the results.\n")
