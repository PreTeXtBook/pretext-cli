import typing as t
import multiprocessing
from pathlib import Path
from lxml import etree as ET
from . import utils


class Target:
    """
    Representation of a target for a PreTeXt project: a specific
    build targeting a format such as HTML, LaTeX, etc.
    """

    # List of valid formats for a target.
    Format = t.Literal[
        "HTML",
        "LATEX",
        "PDF",
        "EPUB",
        "KINDLE",
        "BRAILLE",
        "WEBWORK",
        "CUSTOM",
    ]

    def __init__(
        self,
        name: str,
        frmt: Format,
        source: Path = Path("source", "main.ptx"),
        publication: t.Optional[Path] = None,
        external_dir: t.Optional[Path] = None,
        generated_dir: t.Optional[Path] = None,
        output: t.Optional[Path] = None,
        deploy: t.Optional[Path] = None,
        latex_engine: t.Literal["XELATEX", "LATEX", "PDFLATEX"] = "XELATEX",
    ):
        """
        Construction of a new Target. Requires both a
        `name` and `frmt` (format).
        """
        self.name = name
        self.format = frmt
        self.source = source
        self.publication = publication
        # directories are set by the publication iff it exists
        if publication is None:
            self.external_dir = external_dir
            self.generated_dir = generated_dir
        if output is None:
            self.output = Path("output", name)
        else:
            self.output = output
        self.deploy = deploy
        self.latex_engine = latex_engine

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, path: t.Optional[Path]) -> None:
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
                self._external_dir = path
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
                self._generated_dir = path
        else:
            raise AttributeError("generated_dir is managed by publication")

    def publication_rel_from_source(self) -> Path:
        """
        Provides a relative path to the publication file
        from the source directory.
        """
        return self.publication.relative_to(self.source.parent)


class Project:
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, Paths for where to build output and stage deployments,
    and a list of buildable Targets.
    """

    def __init__(
        self,
        targets: list[Target],
        pth: t.Optional[Path] = None,
        output: t.Optional[Path] = None,
        deploy: t.Optional[Path] = None,
    ):
        self.targets = targets
        if pth is None:
            self.path = Path()
        else:
            self.path = pth
        if output is None:
            self.output = self.path / "output"
        else:
            self.output = self.path / output
        if deploy is None:
            self.deploy = self.path / "deploy"
        else:
            self.deploy = self.path / deploy

    def target(self, name: t.Optional[str]) -> t.Optional[Target]:
        """
        Attempts to return a target matching `name`.
        If `name` isn't provided, returns the default (first) target.
        """
        if len(self.targets) == 0:
            # no target to return
            return None
        if name is None:
            # returns default target
            return self.targets[0]
        try:
            # returns first target matching name
            return next(t for t in self.targets if t.name == name)
        except StopIteration:
            # but no such target was found
            return None

    def server_process(
        self,
        mode: t.Literal["OUTPUT", "DEPLOY"] = "OUTPUT",
        access: t.Literal["PUBLIC", "PRIVATE"] = "PRIVATE",
        port: int = 8000,
        launch: bool = True,
    ) -> multiprocessing.Process:
        """
        Returns a process for running a simple local web server
        providing either the contents of `output` or `deploy`
        """
        if mode == "OUTPUT":
            directory = self.output
        else:  # "DEPLOY"
            directory = self.deploy

        return utils.server_process(directory, access, port, launch=launch)
