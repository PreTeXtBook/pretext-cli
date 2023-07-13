import typing as t
import hashlib
import multiprocessing
import shutil
import tempfile
import pickle
from pathlib import Path
from lxml import etree as ET
import pydantic
from .xml import (
    ProjectXml,
    LegacyProjectXml,
    ExecutablesXml,
    TargetXml,
    LegacyTargetXml,
)
from .. import constants
from .. import core
from .. import utils
from .. import build
from .. import generate
from .. import types as pt  # PreTeXt types


# TODO Not yet used...
# def optstrpth_to_posix(path: t.Optional[t.Union[Path, str]]) -> t.Optional[str]:
#     if path is None:
#         return None
#     else:
#         return Path(path).as_posix()


class Project:
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, and Paths for where to build output and maintain a site.
    """

    def __init__(
        self,
        path: t.Optional[t.Union[Path, str]] = None,
        source: t.Optional[t.Union[Path, str]] = None,
        publication: t.Optional[t.Union[Path, str]] = None,
        output: t.Optional[t.Union[Path, str]] = None,
        site: t.Optional[t.Union[Path, str]] = None,
        xsl: t.Optional[t.Union[Path, str]] = None,
        executables: t.Optional[t.Dict[str, str]] = None,
    ):
        self._targets: t.List[Target] = []
        self.path = path
        self.source = source
        self.publication = publication
        self.output = output
        self.site = site
        self.xsl = xsl
        self.executables = executables

    @classmethod
    def parse(
        cls,
        path: t.Union[Path, str] = Path(),
    ) -> "Project":
        path = Path(path)
        if path.is_dir():
            dir_path = path
            file_path = path / "project.ptx"
        else:
            dir_path = path.parent
            file_path = path
        try:
            project_xml = ProjectXml.from_xml(file_path.read_bytes())
            p = cls(
                path=file_path,
                source=project_xml.source,
                publication=project_xml.publication,
                output=project_xml.output,
                site=project_xml.site,
                xsl=project_xml.xsl,
            )
            p._targets = [
                Target(
                    name=target.name, format=target.format, target_xml=target, project=p
                )
                for target in project_xml.targets
            ]
            exec_path = dir_path / "executables.ptx"
            if exec_path.exists():
                exec_xml = ExecutablesXml.from_xml(exec_path.read_bytes())
                p.executables["latex"] = (
                    exec_xml.latex or constants.EXECUTABLES_DEFAULT["latex"]
                )
                p.executables["pdflatex"] = (
                    exec_xml.pdflatex or constants.EXECUTABLES_DEFAULT["pdflatex"]
                )
                p.executables["xelatex"] = (
                    exec_xml.xelatex or constants.EXECUTABLES_DEFAULT["xelatex"]
                )
                p.executables["pdfsvg"] = (
                    exec_xml.pdfsvg or constants.EXECUTABLES_DEFAULT["pdfsvg"]
                )
                p.executables["asy"] = (
                    exec_xml.asy or constants.EXECUTABLES_DEFAULT["asy"]
                )
                p.executables["sage"] = (
                    exec_xml.sage or constants.EXECUTABLES_DEFAULT["sage"]
                )
                p.executables["pdfpng"] = (
                    exec_xml.pdfpng or constants.EXECUTABLES_DEFAULT["pdfpng"]
                )
                p.executables["pdfeps"] = (
                    exec_xml.pdfeps or constants.EXECUTABLES_DEFAULT["pdfeps"]
                )
                p.executables["node"] = (
                    exec_xml.node or constants.EXECUTABLES_DEFAULT["node"]
                )
                p.executables["liblouis"] = (
                    exec_xml.liblouis or constants.EXECUTABLES_DEFAULT["liblouis"]
                )
            else:
                p.executables = constants.EXECUTABLES_DEFAULT
            return p
        except pydantic.ValidationError as original_error:
            # try legacy
            try:
                project_xml = LegacyProjectXml.from_xml(file_path.read_bytes())
                p = cls(
                    path=file_path,
                    source="",
                    publication="",
                    output="",
                    site="",
                    xsl="",
                )
                p._targets = [
                    Target(
                        name=target.name,
                        format=target.format,
                        legacy_target_xml=target,
                        project=p,
                    )
                    for target in project_xml.targets
                ]
                p.executables["latex"] = (
                    project_xml.executables.latex
                    or constants.EXECUTABLES_DEFAULT["latex"]
                )
                p.executables["pdflatex"] = (
                    project_xml.executables.pdflatex
                    or constants.EXECUTABLES_DEFAULT["pdflatex"]
                )
                p.executables["xelatex"] = (
                    project_xml.executables.xelatex
                    or constants.EXECUTABLES_DEFAULT["xelatex"]
                )
                p.executables["pdfsvg"] = (
                    project_xml.executables.pdfsvg
                    or constants.EXECUTABLES_DEFAULT["pdfsvg"]
                )
                p.executables["asy"] = (
                    project_xml.executables.asy or constants.EXECUTABLES_DEFAULT["asy"]
                )
                p.executables["sage"] = (
                    project_xml.executables.sage
                    or constants.EXECUTABLES_DEFAULT["sage"]
                )
                p.executables["pdfpng"] = (
                    project_xml.executables.pdfpng
                    or constants.EXECUTABLES_DEFAULT["pdfpng"]
                )
                p.executables["pdfeps"] = (
                    project_xml.executables.pdfeps
                    or constants.EXECUTABLES_DEFAULT["pdfeps"]
                )
                p.executables["node"] = (
                    project_xml.executables.node
                    or constants.EXECUTABLES_DEFAULT["node"]
                )
                p.executables["liblouis"] = (
                    project_xml.executables.liblouis
                    or constants.EXECUTABLES_DEFAULT["liblouis"]
                )
                return p
            except pydantic.ValidationError as legacy_error:
                raise original_error and legacy_error

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._path = Path()
        else:
            self._path = constants.PROJECT_DEFAULT["path"]

    @property
    def source(self) -> Path:
        return self._source

    @source.setter
    def source(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._source = constants.PROJECT_DEFAULT["source"]
        else:
            self._source = Path(p)

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._publication = constants.PROJECT_DEFAULT["publication"]
        else:
            self._publication = Path(p)

    @property
    def output(self) -> Path:
        return self._output

    @output.setter
    def output(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._output = constants.PROJECT_DEFAULT["output"]
        else:
            self._output = Path(p)

    @property
    def site(self) -> Path:
        return self._site

    @site.setter
    def site(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._site = constants.PROJECT_DEFAULT["site"]
        else:
            self._site = Path(p)

    @property
    def xsl(self) -> Path:
        return self._xsl

    @xsl.setter
    def xsl(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._xsl = constants.PROJECT_DEFAULT["xsl"]
        else:
            self._xsl = Path(p)

    @property
    def executables(self) -> t.Dict[str, str]:
        return self._executables

    @executables.setter
    def executables(self, ex: t.Optional[t.Dict[str, str]]) -> None:
        if ex is None:
            self._executables = constants.PROJECT_DEFAULT["executables"]
        else:
            self._executables = ex

    @property
    def targets(self) -> t.List["Target"]:
        return self._targets

    def new_target(self, *args, **kwargs) -> None:
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

    def xsl_abspath(self) -> Path:
        return self.abspath() / self.xsl

    def server_process(
        self,
        mode: t.Literal["output", "site"] = "output",
        access: t.Literal["public", "private"] = "private",
        port: int = 8000,
        launch: bool = True,
    ) -> multiprocessing.Process:
        """
        Returns a process for running a simple local web server
        providing either the contents of `output` or `site`
        """
        if mode == "output":
            directory = self.output
        else:  # "site"
            directory = self.site

        return utils.server_process(directory, access, port, launch=launch)


class Target:
    """
    Representation of a target for a PreTeXt project: a specific
    build targeting a format such as HTML, LaTeX, etc.
    """

    def __init__(
        self,
        project: Project,
        name: str,
        format: pt.Format,
        source: t.Optional[t.Union[Path, str]] = None,
        publication: t.Optional[t.Union[Path, str]] = None,
        output: t.Optional[t.Union[Path, str]] = None,
        site: t.Optional[t.Union[Path, str]] = None,
        xsl: t.Optional[t.Union[Path, str]] = None,
        latex_engine: t.Optional[pt.LatexEngine] = None,
        braille_mode: t.Optional[pt.BrailleMode] = None,
        compression: t.Optional[pt.Compression] = None,
        stringparams: t.Dict[str, str] = {},
        target_xml: t.Optional[TargetXml] = None,
        legacy_target_xml: t.Optional[LegacyTargetXml] = None,
    ):
        """
        Construction of a new Target. Requires a `project`,
        `name`, and `format`.
        """
        self._project = project
        self.name = name
        self.format = format
        self.source = source
        self.publication = publication
        self.output = output
        self.site = site
        self.xsl = xsl
        self.latex_engine = latex_engine
        self.braille_mode = braille_mode
        self.compression = compression
        self.stringparams = stringparams
        if target_xml is not None:
            self.source = target_xml.source
            self.publication = target_xml.publication
            self.output = target_xml.output
            self.site = target_xml.site
            self.xsl = target_xml.xsl
            self.latex_engine = target_xml.latex_engine
            self.braille_mode = target_xml.braille_mode
            self.compression = target_xml.compression
            self.stringparams = {
                param.key: param.value for param in target_xml.stringparams
            }
        elif legacy_target_xml is not None:
            self.source = legacy_target_xml.source
            self.publication = legacy_target_xml.publication
            self.output = legacy_target_xml.output_dir
            self.site = legacy_target_xml.site
            self.xsl = legacy_target_xml.xsl
            self.latex_engine = legacy_target_xml.pdf_method
            self.braille_mode = None
            self.compression = None
            if legacy_target_xml.format == "html-zip":
                self.format = "html"
                self.compression = "zip"
            elif legacy_target_xml.format == "webwork-sets":
                self.format = "webwork"
            elif legacy_target_xml.format == "webwork-sets-zipped":
                self.format = "webwork"
                self.compression = "zip"
            elif legacy_target_xml.format == "braille-electronic":
                self.format = "braille"
                self.braille_mode = "electronic"
            elif format == "braille-emboss":
                self.format = "braille"
            self.stringparams = {
                param.key: param.value for param in legacy_target_xml.stringparams
            }

    @property
    def project(self) -> Project:
        return self._project

    @property
    def source(self) -> Path:
        return self._source

    @source.setter
    def source(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._source = constants.TARGET_DEFAULT["source"]
        else:
            self._source = Path(path)

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._publication = constants.TARGET_DEFAULT["publication"]
        else:
            self._publication = Path(path)

    @property
    def output(self) -> Path:
        return self._output

    @output.setter
    def output(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._output = Path(self.name)
        else:
            self._output = Path(path)

    @property
    def site(self) -> Path:
        return self._site

    @site.setter
    def site(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._site = constants.TARGET_DEFAULT["site"]
        else:
            self._site = Path(path)

    @property
    def xsl(self) -> t.Optional[Path]:
        return self._xsl

    @xsl.setter
    def xsl(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._xsl = constants.TARGET_DEFAULT["xsl"]
        else:
            self._xsl = Path(p)

    @property
    def latex_engine(self) -> pt.LatexEngine:
        return self._latex_engine

    @latex_engine.setter
    def latex_engine(self, engine: t.Optional[pt.LatexEngine]) -> None:
        if engine is None:
            self._latex_engine = constants.TARGET_DEFAULT["latex_engine"]
        else:
            self._latex_engine = engine

    @property
    def braille_mode(self) -> pt.LatexEngine:
        return self._latex_engine

    @braille_mode.setter
    def braille_mode(self, mode: t.Optional[pt.BrailleMode]) -> None:
        if mode is None:
            self._braille_mode = constants.TARGET_DEFAULT["braille_mode"]
        else:
            self._braille_mode = mode

    @property
    def compression(self) -> Path:
        return self._compression

    @compression.setter
    def compression(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._compression = constants.TARGET_DEFAULT["compression"]
        else:
            self._compression = Path(path)

    def source_abspath(self) -> Path:
        return self.project.source_abspath() / self.source

    def source_element(self) -> ET._Element:
        source_doc = ET.parse(self.source_abspath())
        for _ in range(25):
            source_doc.xinclude()
        return source_doc.getroot()

    def publication_abspath(self) -> Path:
        return self.project.publication_abspath() / self.publication

    def output_abspath(self) -> Path:
        return self.project.output_abspath() / self.output

    def output_dir_abspath(self) -> Path:
        if self.output_abspath().is_dir():
            return self.output_abspath()
        else:
            return self.output_abspath().parent

    def output_filename(self) -> t.Optional[str]:
        if self.output_abspath().is_dir():
            return None
        else:
            return self.output_abspath().name

    def xsl_abspath(self) -> t.Optional[Path]:
        if self.xsl is None:
            return None
        return self.project.xsl_abspath() / self.xsl

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

    def load_asset_table(self) -> pt.AssetTable:
        """
        Loads the asset table from a pickle file in the generated assets directory
        based on the target name.
        """
        try:
            with open(
                self.generated_dir_abspath() / f".{self.name}_assets.pkl", "rb"
            ) as f:
                return pickle.load(f)
        except Exception:
            return {}

    def generate_asset_table(self) -> pt.AssetTable:
        asset_hash_dict: pt.AssetTable = {}
        for asset in constants.ASSET_TO_XPATH.keys():
            if asset == "webwork":
                # WeBWorK must be regenerated every time *any* of the ww exercises change.
                ww = self.source_element().xpath(".//webwork[@*|*]")
                assert isinstance(ww, t.List)
                if len(ww) == 0:
                    # Only generate a hash if there are actually ww exercises in the source
                    continue
                asset_hash_dict["webwork"] = {}
                h = hashlib.sha256()
                for node in ww:
                    assert isinstance(node, ET._Element)
                    h.update(ET.tostring(node))
                asset_hash_dict["webwork"][""] = h.digest()
            else:
                # everything else can be updated individually, if it has an xml:id
                source_assets = self.source_element().xpath(
                    f".//{constants.ASSET_TO_XPATH[asset]}"
                )
                assert isinstance(source_assets, t.List)
                if len(source_assets) == 0:
                    # Only generate a hash if there are actually assets of this type in the source
                    continue
                asset_hash_dict[asset] = {}
                h_no_id = hashlib.sha256()
                for node in source_assets:
                    assert isinstance(node, ET._Element)
                    # First see if the node has an xml:id, or if it is a child of a node with an xml:id that hasn't already been used
                    if (
                        (id := node.xpath("@xml:id") or node.xpath("parent::*/@xml:id"))
                        and isinstance(id, t.List)
                        and id[0] not in asset_hash_dict[asset]
                    ):
                        assert isinstance(id[0], str)
                        asset_hash_dict[asset][id[0]] = hashlib.sha256(
                            ET.tostring(node)
                        ).digest()
                    # otherwise collect all non-id'd nodes into a single hash
                    else:
                        h_no_id.update(ET.tostring(node))
                        asset_hash_dict[asset][""] = h_no_id.digest()
        return asset_hash_dict

    def save_asset_table(self, asset_table: pt.AssetTable) -> None:
        """
        Saves the asset_table to a pickle file in the generated assets directory
        based on the target name.
        """
        with open(self.generated_dir_abspath() / f".{self.name}_assets.pkl", "wb") as f:
            pickle.dump(asset_table, f)

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
        generate_assets: bool = True,
        xmlid: t.Optional[str] = None,
        log_info: t.Callable = print,
        log_warning: t.Callable = print,
    ) -> None:
        # Check for xml syntax errors and quit if xml invalid:
        if not utils.xml_syntax_is_valid(self.source_abspath()):
            raise RuntimeError("XML syntax for source file is invalid")
        if not utils.xml_syntax_is_valid(self.publication_abspath(), "publication"):
            raise RuntimeError("XML syntax for publication file is invalid")
        # Validate xml against schema; continue with warning if invalid:
        utils.xml_source_validates_against_schema(self.source_abspath())

        # Clean output upon request
        if clean:
            self.clean_output()

        # Ensure the asset directories exist.
        self.ensure_asset_directories()

        if generate_assets:
            self.generate_assets()

        with tempfile.TemporaryDirectory() as tmp_xsl_str:
            tmp_xsl_path = Path(tmp_xsl_str)
            # if custom xsl, copy it into a temporary directory (different from the building temporary directory)
            if (txp := self.xsl_abspath()) is not None:
                log_info(f"Building with custom xsl {txp}")
                utils.copy_custom_xsl(txp, tmp_xsl_path)
                custom_xsl = tmp_xsl_path / txp.name
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

            build.build(
                self.format,
                self.source_abspath(),
                self.publication_abspath(),
                self.output_abspath(),
                self.stringparams,
                custom_xsl=custom_xsl,
                xmlid=xmlid,
                zipped=self.compression is not None,
                project_path=self.project.abspath(),
                latex_engine=self.latex_engine,
                executables=self.project.executables,
                braille_mode=self.braille_mode,
            )
        # build was successful
        log_info("\nSuccess! Run `pretext view` to see the results.\n")

    def generate_assets(
        self,
        specified_asset_types: t.Optional[t.List[str]] = None,
        all_formats: bool = False,
        check_cache: bool = True,
        xmlid: t.Optional[str] = None,
        log_info: t.Callable = print,
    ) -> None:
        if specified_asset_types is None:
            specified_asset_types = list(constants.ASSET_TO_XPATH.keys())
        if check_cache:
            # TODO this ignores xmlid!
            asset_table_cache = self.load_asset_table()
            asset_table = self.generate_asset_table()
            if asset_table == asset_table_cache:
                log_info("All generated assets were found within the cache.")
            else:
                # Loop over assets used in the document.
                for asset in specified_asset_types:
                    # This asset type was not used.
                    if asset not in asset_table:
                        log_info(f"No {asset} were found in the document.")
                    # A new asset was used, so regenerate everything.
                    elif asset not in asset_table_cache:
                        log_info(
                            f"{asset} was found, but no {asset} were previously cached. "
                            + f"Regenerating all {asset}."
                        )
                        self.generate_assets(
                            specified_asset_types=[asset],
                            all_formats=all_formats,
                            check_cache=False,
                            xmlid=None,
                            log_info=log_info,
                        )
                    # The asset was used previously.
                    elif asset_table.get(asset) != asset_table_cache.get(asset):
                        asset_ids = asset_table.get(asset)
                        cached_asset_ids = asset_table_cache.get(asset)
                        if asset_ids is not None and cached_asset_ids is not None:
                            # Check each hashed id
                            for id in asset_ids:
                                # A change has occurred.
                                if asset_ids.get(id) != cached_asset_ids.get(id):
                                    # No xmlid is associated
                                    if id == "":
                                        # Webwork never stores an xmlid
                                        if asset != "webwork":
                                            log_info(
                                                f"{asset} has been modified since the last generation, but lacks an xmlid. "
                                                + f"Regenerating all {asset}."
                                            )
                                        else:
                                            log_info(
                                                "WebWork has been modified since the last generation. "
                                                + "Regenerating all WebWork."
                                            )
                                        self.generate_assets(
                                            specified_asset_types=[asset],
                                            all_formats=all_formats,
                                            check_cache=False,
                                            xmlid=None,
                                            log_info=log_info,
                                        )
                                    # We have an xmlid we can focus on
                                    else:
                                        log_info(
                                            f"{asset} associated with xmlid `{id}` has been modified since the last generation. "
                                            + "Regenerating."
                                        )
                                        self.generate_assets(
                                            specified_asset_types=[asset],
                                            all_formats=all_formats,
                                            check_cache=False,
                                            xmlid=id,
                                            log_info=log_info,
                                        )
                    # Nothing about this asset has changed.
                    else:
                        log_info(
                            f"No {asset} has been modified since the last generation."
                        )
                self.save_asset_table(asset_table)
            return

        # set executables
        core.set_executables(self.project.executables)

        # build targets:
        try:
            if "webwork" in specified_asset_types:
                generate.webwork(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath() / "webwork",
                    self.stringparams,
                    xmlid,
                )
            if "latex-image" in specified_asset_types:
                generate.latex_image(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    self.format,
                    xmlid,
                    self.latex_engine,
                    all_formats,
                )
            if "asymptote" in specified_asset_types:
                generate.asymptote(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    self.format,
                    xmlid,
                    all_formats,
                )
            if "sageplot" in specified_asset_types:
                generate.sageplot(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    self.format,
                    xmlid,
                    all_formats,
                )
            if "interactive" in specified_asset_types:
                generate.interactive(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
            if "youtube" in specified_asset_types:
                generate.youtube(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
                generate.play_button(
                    self.generated_dir_abspath(),
                )
            if "codelens" in specified_asset_types:
                generate.codelens(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
            if "datafile" in specified_asset_types:
                generate.datafiles(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
            if (
                "interactive" in specified_asset_types
                or "youtube" in specified_asset_types
            ):
                generate.qrcodes(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
        finally:
            # Delete temporary directories left behind by core:
            core.release_temporary_directories()
