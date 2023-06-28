import typing as t
import multiprocessing
from pathlib import Path
from lxml import etree as ET
from . import utils


class Project:
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, and Paths for where to build output and stage deployments.
    """

    def __init__(
        self,
        path: t.Optional[Path | str] = None,
        output: t.Optional[Path | str] = None,
        deploy: t.Optional[Path | str] = None,
    ):
        self._targets: list[Target] = []
        self.path = path
        self.output = output
        self.deploy = deploy

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
        output = element.get("output")
        deploy = element.get("deploy")
        project = cls(path=dir_path, output=output, deploy=deploy)
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
            # returns default target
            return self._targets[0]
        try:
            # returns first target matching name
            return next(t for t in self._targets if t.name == name)
        except StopIteration:
            # but no such target was found
            return None

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

    def __init__(
        self,
        project: Project,
        name: str,
        format: Format,
        source: t.Optional[Path | str] = None,
        publication: t.Optional[Path | str] = None,
        external_dir: t.Optional[Path | str] = None,
        generated_dir: t.Optional[Path | str] = None,
        output: t.Optional[Path | str] = None,
        deploy: t.Optional[Path | str] = None,
        latex_engine: t.Literal["xelatex", "latex", "pdflatex"] = "xelatex",
    ):
        """
        Construction of a new Target. Requires both a
        `name` and `format`.
        """
        self._project = project
        self.name = name
        self.format = format
        self.source = source
        # directories are set by the publication iff it exists
        if publication is None:
            self.publication = None
            self.external_dir = external_dir
            self.generated_dir = generated_dir
        else:
            self.publication = publication
        self.output = output
        self.deploy = deploy
        self.latex_engine = latex_engine

    @classmethod
    def parse(
        cls,
        project: Project,
        element: ET._Element,
    ) -> "Target":
        latex_engine = element.get("latex-engine")
        if latex_engine is not None:
            latex_engine = latex_engine.lower()
        return cls(
            project,
            element.get("name"),
            element.get("format").lower(),
            source=element.get("source"),
            publication=element.get("publication"),
            output=element.get("output"),
            deploy=element.get("deploy"),
            latex_engine=latex_engine,
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
        self._publication = path
        if path is not None:
            pub_ele = ET.parse(path).getroot()
            dir_ele = pub_ele.find("source").find("directories")
            self.external_dir = self.source / dir_ele.get("external")
            self.generated_dir = self.source / dir_ele.get("generated")
        else:
            self.external_dir = None  # use default
            self.generated_dir = None  # use default

    @property
    def external_dir(self) -> Path:
        return self._external_dir

    @external_dir.setter
    def external_dir(self, path: t.Optional[Path]) -> None:
        if self.publication is None:
            if path is None:
                self._external_dir = Path("assets")
            else:
                self._external_dir = Path(path)
        else:
            raise AttributeError("external_dir is managed by publication")

    @property
    def generated_dir(self) -> Path:
        return self._generated_dir

    @generated_dir.setter
    def generated_dir(self, path: t.Optional[Path]) -> None:
        if self.publication is None:
            if path is None:
                self._generated_dir = Path("generated-assets")
            else:
                self._generated_dir = Path(path)
        else:
            raise AttributeError("generated_dir is managed by publication")

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
