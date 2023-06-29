import typing as t
import hashlib
import multiprocessing
import shutil
import tempfile
import pickle
from pathlib import Path
from lxml import etree as ET
from . import ASSETS
from . import core
from . import utils
from . import build
from . import generate

AssetTable = t.Dict[t.Tuple[str, str], bytes]


class Project:
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, and Paths for where to build output and maintain a site.
    """

    DEFAULT = {
        "path": Path(),
        "source": Path("source"),
        "publication": Path("publication"),
        "output": Path("output"),
        "site": Path("site"),
        "xsl": Path("xsl"),
        "executables": {
            "latex": "latex",
            "pdflatex": "pdflatex",
            "xelatex": "xelatex",
            "pdfsvg": "pdf2svg",
            "asy": "asy",
            "sage": "sage",
            "pdfpng": "convert",
            "pdfeps": "pdftops",
            "node": "node",
            "liblouis": "file2brl",
        },
    }

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
        if element.get("ptx-version") == "2":
            if (dir_path / "executables.ptx").exists():
                exec_ele = ET.parse(dir_path / "executables.ptx").getroot()
                executables = cls().DEFAULT["executables"]
                for key in executables:
                    if exec_ele.get(key) is not None:
                        executables[key] = exec_ele.get(key)
            else:
                executables = None
            project = cls(
                path=dir_path,
                source=element.get("source"),
                publication=element.get("publication"),
                output=element.get("output"),
                site=element.get("site"),
                xsl=element.get("xsl"),
                executables=executables,
            )
            for t_ele in element.findall("./targets/target"):
                project.parse_target(t_ele)
            return project
        else:
            if element.find("executables") is None:
                executables = None
            else:
                executables = cls().DEFAULT["executables"]
                for key in executables:
                    if element.find("executables").find(key) is not None:
                        executables[key] = element.find("executables").find(key).text
            # parse the old project manifest format
            project = cls(
                path=dir_path,
                source=Path(""),
                publication=Path(""),
                output=Path(""),
                site=Path(""),
                xsl=Path(""),
                executables=executables,
            )
            for t_ele in element.findall("./targets/target"):
                project.parse_target(t_ele, legacy=True)
            return project

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._path = Path()
        else:
            self._path = self.DEFAULT["path"]

    @property
    def source(self) -> Path:
        return self._source

    @source.setter
    def source(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._source = self.DEFAULT["source"]
        else:
            self._source = Path(p)

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._publication = self.DEFAULT["publication"]
        else:
            self._publication = Path(p)

    @property
    def output(self) -> Path:
        return self._output

    @output.setter
    def output(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._output = self.DEFAULT["output"]
        else:
            self._output = Path(p)

    @property
    def site(self) -> Path:
        return self._site

    @site.setter
    def site(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._site = self.DEFAULT["site"]
        else:
            self._site = Path(p)

    @property
    def xsl(self) -> Path:
        return self._xsl

    @xsl.setter
    def xsl(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._xsl = self.DEFAULT["xsl"]
        else:
            self._xsl = Path(p)

    @property
    def executables(self) -> t.Dict[str, str]:
        return self._executables

    @executables.setter
    def executables(self, ex: t.Optional[t.Dict[str, str]]) -> None:
        if ex is None:
            self._executables = self.DEFAULT["executables"]
        else:
            self._executables = ex

    @property
    def targets(self) -> t.List["Target"]:
        return self._targets

    def parse_target(self, element: ET._Element, legacy: bool = False) -> None:
        self._targets.append(Target.parse(self, element, legacy=legacy))

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

    DEFAULT = {
        "source": Path("main.ptx"),
        "publication": Path("publication.ptx"),
        # "output" depends on name
        "site": None,
        "xsl": None,
        "latex_engine": "xelatex",
        "stringparams": {},
    }

    def __init__(
        self,
        project: Project,
        name: str,
        format: Format,
        source: t.Optional[t.Union[Path, str]] = None,
        publication: t.Optional[t.Union[Path, str]] = None,
        output: t.Optional[t.Union[Path, str]] = None,
        site: t.Optional[t.Union[Path, str]] = None,
        xsl: t.Optional[t.Union[Path, str]] = None,
        latex_engine: t.Optional[LatexEngine] = None,
        stringparams: t.Dict[str, str] = {},
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
        self.site = site
        self.xsl = xsl
        self.latex_engine = latex_engine
        self.stringparams = stringparams

    @classmethod
    def parse(
        cls, project: Project, element: ET._Element, legacy: bool = False
    ) -> "Target":
        stringparams = {}
        for param in element.findall("stringparam"):
            if param.get("key") is None or param.get("value") is None:
                raise ValueError("stringparam must have a key and value")
            stringparams[param.get("key")] = param.get("value")
        if legacy:
            if element.find("source") is None:
                source = None
            else:
                source = element.find("source").text
            if element.find("publication") is None:
                publication = None
            else:
                publication = element.find("publication").text
            if element.find("output-dir") is None:
                output = None
            else:
                output = element.find("output-dir").text
            if element.find("site") is None:
                site = None
            else:
                site = element.find("site").text
            if element.find("xsl") is None:
                xsl = None
            else:
                xsl = element.find("xsl").text
            return cls(
                project,
                element.get("name"),
                element.find("format").text,
                source=source,
                publication=publication,
                output=output,
                site=site,
                xsl=xsl,
                latex_engine=element.get("pdf-method"),
                stringparams=stringparams,
            )
        else:
            return cls(
                project,
                element.get("name"),
                element.get("format"),
                source=element.get("source"),
                publication=element.get("publication"),
                output=element.get("output"),
                site=element.get("site"),
                xsl=element.get("xsl"),
                latex_engine=element.get("latex-engine"),
                stringparams=stringparams,
            )

    @property
    def project(self) -> Project:
        return self._project

    @property
    def source(self) -> Path:
        return self._source

    @source.setter
    def source(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._source = self.DEFAULT["source"]
        else:
            self._source = Path(path)

    @property
    def publication(self) -> Path:
        return self._publication

    @publication.setter
    def publication(self, path: t.Optional[t.Union[Path, str]]) -> None:
        if path is None:
            self._publication = self.DEFAULT["publication"]
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
            self._site = self.DEFAULT["site"]
        else:
            self._site = Path(path)

    @property
    def xsl(self) -> t.Optional[Path]:
        return self._xsl

    @xsl.setter
    def xsl(self, p: t.Optional[t.Union[Path, str]]) -> None:
        if p is None:
            self._xsl = self.DEFAULT["xsl"]
        else:
            self._xsl = Path(p)

    @property
    def latex_engine(self) -> LatexEngine:
        return self._latex_engine

    @latex_engine.setter
    def latex_engine(self, engine: t.Optional[LatexEngine]) -> None:
        if engine is None:
            self._latex_engine = self.DEFAULT["latex_engine"]
        else:
            self._latex_engine = engine

    def source_abspath(self) -> Path:
        return self.project.source_abspath() / self.source

    def source_element(self) -> ET._Element:
        return ET.parse(self.source_abspath()).getroot()

    def publication_abspath(self) -> Path:
        return self.project.publication_abspath() / self.publication

    def output_abspath(self) -> Path:
        return self.project.output_abspath() / self.output

    def output_dir_abspath(self) -> Path:
        if self.output_abspath().is_dir():
            return self.output_abspath()
        else:
            return self.output_abspath().parent

    def output_filename(self) -> t.Optional[Path]:
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

    def load_asset_table(self) -> AssetTable:
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

    def generate_asset_table(self) -> AssetTable:
        asset_hash_dict = {}
        for asset in ASSETS:
            if asset == "webwork":
                ww = self.source_element().xpath(".//webwork[@*|*]")
                assert isinstance(ww, t.List)
                # WeBWorK must be regenerated every time *any* of the ww exercises change.
                if len(ww) == 0:
                    # Only generate a hash if there are actually ww exercises in the source
                    continue
                h = hashlib.sha256()
                for node in ww:
                    assert isinstance(node, ET._Element)
                    h.update(ET.tostring(node))
                asset_hash_dict[(asset, "")] = h.digest()
            elif asset != "ALL":
                # everything else can be updated individually, if it has an xml:id
                source_assets = self.source_element().xpath(f".//{asset}")
                assert isinstance(source_assets, t.List)
                if len(source_assets) == 0:
                    # Only generate a hash if there are actually assets of this type in the source
                    continue
                h_no_id = hashlib.sha256()
                for node in source_assets:
                    assert isinstance(node, ET._Element)
                    # First see if the node has an xml:id, or if it is a child of a node with an xml:id (but we haven't already made this key)
                    if (
                        (id := node.xpath("@xml:id") or node.xpath("parent::*/@xml:id"))
                        and isinstance(id, t.List)
                        and (asset, id[0]) not in asset_hash_dict
                    ):
                        assert isinstance(id[0], str)
                        asset_hash_dict[(asset, id[0])] = hashlib.sha256(
                            ET.tostring(node)
                        ).digest()
                    # otherwise collect all non-id'd nodes into a single hash
                    else:
                        h_no_id.update(ET.tostring(node))
                asset_hash_dict[(asset, "")] = h_no_id.digest()
        return asset_hash_dict

    def save_asset_table(self, asset_table: AssetTable) -> None:
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
            # # TODO move caching stuff to generate method
            # asset_table_cache = self.load_asset_table()
            # asset_table = self.generate_asset_table()
            # if asset_table == asset_table_cache:
            #     log_info(
            #         "No change in assets requiring generating detected.  To force regeneration of assets, use `-g` flag.\n"
            #     )
            # else:
            #     for asset in set(asset[0] for asset in asset_table.keys()):
            #         if asset in ["webwork"]:
            #             if (asset, "") not in asset_table or asset_table[
            #                 (asset, "")
            #             ] != asset_table[(asset, "")]:
            #                 self.generate(asset_list=[asset])
            #         elif (asset, "") not in asset_table or asset_table[
            #             (asset, "")
            #         ] != asset_table[(asset, "")]:
            #             self.generate(asset_list=[asset])
            #         else:
            #             for id in set(
            #                 key[1] for key in asset_table.keys() if key[0] == asset
            #             ):
            #                 if (asset, id) not in asset_table or asset_table[
            #                     (asset, id)
            #                 ] != asset_table[(asset, id)]:
            #                     log_info(
            #                         f"\nIt appears the source has changed of an asset that needs to be generated.  Now generating asset: {asset} with xmlid: {id}."
            #                     )
            #                     self.generate(asset_list=[asset], xmlid=id)
            #     self.save_asset_table(asset_table)

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

            # set executables
            core.set_executables(self.project.executables)

            # try to build
            try:
                if self.format == "html":
                    build.html(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                        xmlid,
                        zipped=False,
                        project_path=self.project.abspath(),
                    )
                elif self.format == "html-zip":
                    build.html(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                        xmlid,
                        zipped=True,
                        project_path=self.project.abspath(),
                    )
                elif self.format == "latex":
                    build.latex(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                    )
                    # Manually copy over asset directories
                    shutil.copytree(
                        self.external_dir_abspath(),
                        self.output_abspath() / "external",
                        dirs_exist_ok=True,
                    )
                    shutil.copytree(
                        self.generated_dir_abspath(),
                        self.output_abspath() / "generated",
                        dirs_exist_ok=True,
                    )
                elif self.format == "pdf":
                    build.pdf(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        custom_xsl,
                        self.latex_engine,
                    )
                elif self.format == "custom":
                    if custom_xsl is None:
                        raise RuntimeError("Must specify custom XSL for custom build.")
                    build.custom(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_dir_abspath(),
                        self.stringparams,
                        custom_xsl,
                        output_filename=self.output_filename(),
                    )
                elif self.format == "epub":
                    build.epub(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                    )
                elif self.format == "kindle":
                    build.kindle(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                    )
                elif self.format in ("braille", "braille-emboss"):
                    build.braille(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        page_format="emboss",
                    )
                elif self.format == "braille-electronic":
                    build.braille(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        page_format="electronic",
                    )
                elif self.format == "webwork-sets":
                    build.webwork_sets(
                        self.source_abspath(),
                        self.publication_abspath(),
                        self.output_abspath(),
                        self.stringparams,
                        False,
                    )
                elif self.format == "webwork-sets-zip":
                    build.webwork_sets(
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
            # except Exception:
            #     pass  # TODO handle in CLI
            finally:
                # remove temp directories left by core.
                core.release_temporary_directories()
        # build was successful
        log_info("\nSuccess! Run `pretext view` to see the results.\n")

    def generate_assets(
        self,
        asset_tags: t.Optional[t.List[str]] = None,
        all_formats: bool = False,
        xmlid: t.Optional[str] = None,
    ) -> None:
        # set executables
        core.set_executables(self.project.executables)

        # build targets:
        try:
            if asset_tags is None or "webwork" in asset_tags:
                webwork_output = self.generated_dir_abspath() / "webwork"
                generate.webwork(
                    self.source_abspath(),
                    self.publication_abspath(),
                    webwork_output,
                    self.stringparams,
                    xmlid,
                )
            if asset_tags is None or "latex-image" in asset_tags:
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
            if asset_tags is None or "asymptote" in asset_tags:
                generate.asymptote(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    self.format,
                    xmlid,
                    all_formats,
                )
            if asset_tags is None or "sageplot" in asset_tags:
                generate.sageplot(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    self.format,
                    xmlid,
                    all_formats,
                )
            if asset_tags is None or "interactive" in asset_tags:
                generate.interactive(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
            if asset_tags is None or "youtube" in asset_tags:
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
            if asset_tags is None or "codelens" in asset_tags:
                generate.codelens(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
            if asset_tags is None or "datafile" in asset_tags:
                generate.datafiles(
                    self.source_abspath(),
                    self.publication_abspath(),
                    self.generated_dir_abspath(),
                    self.stringparams,
                    xmlid,
                )
            if (
                asset_tags is None
                or "interactive" in asset_tags
                or "youtube" in asset_tags
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
