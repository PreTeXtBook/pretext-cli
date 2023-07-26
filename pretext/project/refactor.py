import typing as t
from enum import Enum
import hashlib
import multiprocessing
import shutil
import tempfile
import pickle
from pathlib import Path
from lxml import etree as ET
from pydantic import validator, PrivateAttr
import pydantic_xml as pxml
from .xml import Executables, LegacyProject, LatexEngine
from .. import constants
from .. import core
from .. import utils
from .. import build
from .. import generate
from .. import types as pt  # PreTeXt types
from .. import templates


# TODO Not yet used...
# def optstrpth_to_posix(path: t.Optional[t.Union[Path, str]]) -> t.Optional[str]:
#     if path is None:
#         return None
#     else:
#         return Path(path).as_posix()


class Format(str, Enum):
    HTML = "html"
    LATEX = "latex"
    PDF = "pdf"
    EPUB = "epub"
    KINDLE = "kindle"
    BRAILLE = "braille"
    WEBWORK = "webwork"
    CUSTOM = "custom"


# The CLI only needs two values from the publication file. Therefore, this class ignores the vast majority of a publication file's contents, loading and validating only a (small) relevant subset.
class PublicationSubset(pxml.BaseXmlModel, tag="publication", search_mode="unordered"):
    external: Path = pxml.wrapped("source/directories", pxml.attr())
    generated: Path = pxml.wrapped("source/directories", pxml.attr())


class BrailleMode(str, Enum):
    EMBOSS = "emboss"
    ELECTRONIC = "electronic"


class Compression(str, Enum):
    ZIP = "zip"


class Target(pxml.BaseXmlModel, tag="target"):
    """
    Representation of a target for a PreTeXt project: a specific
    build targeting a format such as HTML, LaTeX, etc.
    """

    # Provide access to the containing project.
    _project: "Project" = PrivateAttr()
    name: str = pxml.attr()
    format: Format = pxml.attr()
    # A path to the root source for this target, relative to the project's `source` path.
    source: Path = pxml.attr(default=Path("main.ptx"))
    # A path to the publication file for this target, relative to the project's `publication` path.
    publication: Path = pxml.attr(default=None)

    # If no publication file is specified, assume either `publication.ptx` (if it exists) or the CLI's template `publication.ptx` (which always exists). If a publication file is specified, ensure that it exists.
    #
    # This can't be placed in a Pydantic validator, since `self._project` isn't set until after validation finishes. So, this must be manually called after that's done.
    def post_validate_publication(self) -> None:
        if self.publication is None:
            self.publication = Path("publication.ptx")
            if self.publication_abspath().exists():
                return
            # TODO: this is wrong, since the returned path is only valid inside the context manager. Instead, need to enter the context here, then exit it when this class is deleted (also problematic).
            with templates.resource_path("publication.ptx") as self.publication:
                return
        p_full = self.publication_abspath()
        if not p_full.exists():
            raise FileNotFoundError(
                f"Provided publication file {p_full} does not exist."
            )

    # A path to the output directory for this target, relative to the project's `output` path.
    output: Path = pxml.attr(default=None)

    # Make the default value for output be `self.name`. Specifying a `default_factory` won't work, since it's a `@classmethod`. So, use a validator (which has access to the object), replacing `None` (hack: a type violation) with `self.name`.
    @validator("output", always=True)
    def output_defaults_to_name(cls, v: t.Optional[Path], values: t.Any) -> Path:
        return Path(v) if v is not None else Path(values["name"])

    # A path to the subdirectory of your GitHub page where a book will be deployed for this target, relative to the project's `site` path.
    site: Path = pxml.attr(default=Path("site"))
    # A path to custom XSL for this target, relative to the project's `xsl` path.
    xsl: t.Optional[Path] = pxml.attr(default=None)

    # If the `format == Format.CUSTOM`, then `xsl` must be defined.
    @validator("xsl")
    def xsl_validator(cls, v: t.Optional[Path], values: t.Any) -> t.Optional[Path]:
        if v is None and values["format"] == Format.CUSTOM:
            raise ValueError("A custom format requires a value for xsl.")
        return v

    latex_engine: LatexEngine = pxml.attr(
        name="latex-engine", default=LatexEngine.XELATEX
    )
    braille_mode: BrailleMode = pxml.attr(
        name="braille-mode", default=BrailleMode.EMBOSS
    )
    compression: t.Optional[Compression] = pxml.attr()
    stringparams: t.Dict[str, str] = pxml.element(default={})

    # Allow specifying `_project` in the constructor. (Since it's private, pydantic ignores it by default).
    def __init__(self, **kwargs: t.Any):
        super().__init__(**kwargs)
        if "_project" in kwargs:
            self._project = kwargs["_project"]
            # Since we now have the project, perform validation.
            self.post_validate_publication()

    def source_abspath(self) -> Path:
        return self._project.source_abspath() / self.source

    def source_element(self) -> ET._Element:
        source_doc = ET.parse(self.source_abspath())
        for _ in range(25):
            source_doc.xinclude()
        return source_doc.getroot()

    def publication_abspath(self) -> Path:
        return self._project.publication_abspath() / self.publication

    def output_abspath(self) -> Path:
        return self._project.output_abspath() / self.output

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
        return self._project.xsl_abspath() / self.xsl

    def _read_publication_file_subset(self) -> PublicationSubset:
        p_bytes = self.publication_abspath().read_bytes()
        return PublicationSubset.from_xml(p_bytes)

    def external_dir(self) -> Path:
        return self._read_publication_file_subset().external

    def external_dir_abspath(self) -> Path:
        return (self.source_abspath().parent / self.external_dir()).resolve()

    def generated_dir(self) -> Path:
        return self._read_publication_file_subset().generated

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
        if self._project.abspath() not in self.output_abspath().parents:
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
                project_path=self._project.abspath(),
                latex_engine=self.latex_engine,
                executables=self._project._executables.dict(),
                # TODO: what if this isn't defined? Should we have a default in the project file instead?
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
        core.set_executables(self._project._executables.dict())

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


class Project(pxml.BaseXmlModel, tag="project"):
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, and Paths for where to build output and maintain a site.
    """

    ptx_version: t.Literal["2"] = pxml.attr(name="ptx-version")
    _executables: Executables = PrivateAttr(default=Executables())
    # A path, relative to the project directory (defined by `self.abspath()`), prepended to any target's `source`.
    source: Path = pxml.attr(default=Path("source"))
    # The absolute path of the project file (typically, `project.ptx`).
    _path: Path = PrivateAttr(default=Path("."))

    # Allow a relative path; if it's a directory, assume a `project.ptx` suffix. Make the path absolute.
    @classmethod
    def validate_path(cls, path: t.Union[Path, str]) -> Path:
        path = Path(path).resolve()
        # Note: we don't require the `project.ptx` file to exist, since this can be created from API calls instead of being read in from a project file.
        return path / "project.ptx" if path.is_dir() else path

    # A path, relative to the project directory, prepended to any target's `publication`.
    publication: Path = pxml.attr(default=Path("publication"))
    # A path, relative to the project directory, prepended to any target's `output`.
    output: Path = pxml.attr(default=Path("output"))
    # A path, relative to the project directory, prepended to any target's `site`.
    site: Path = pxml.attr(default=Path("site"))
    # A path, relative to the project directory, prepended to any target's `xsl`.
    xsl: Path = pxml.attr(default=Path("xsl"))
    targets: t.List[Target] = pxml.wrapped(
        "targets", pxml.element(tag="target", default=[])
    )

    # Allow specifying `_path` or `_executables` in the constructor. (Since they're private, pydantic ignores them by default).
    def __init__(self, **kwargs: t.Any):
        super().__init__(**kwargs)
        for k in ("_path", "_executables"):
            if k in kwargs:
                setattr(self, k, kwargs[k])
        self._path = self.validate_path(self._path)

    @classmethod
    def parse(
        cls,
        path: t.Union[Path, str] = Path("."),
    ) -> "Project":
        _path = cls.validate_path(path)
        # TODO: nicer errors if these files aren't found.
        xml_bytes = _path.read_bytes()

        # Determine the version of this project file.
        class ProjectVersionOnly(pxml.BaseXmlModel, tag="project"):
            ptx_version: t.Optional[str] = pxml.attr(name="ptx-version")

        p_version_only = ProjectVersionOnly.from_xml(xml_bytes)
        if p_version_only.ptx_version is not None:
            p = Project.from_xml(xml_bytes)

            # Now that the project is loaded, load / set up what isn't in the project XML.
            p._path = _path
            try:
                e_bytes = (p._path.parent / "executables.ptx").read_bytes()
            except FileNotFoundError:
                # If this isn't found, use the already-set default value.
                pass
            else:
                p._executables = Executables.from_xml(e_bytes)

        else:
            legacy_project = LegacyProject.from_xml(_path.read_bytes())
            # Translate from old target format to new target format.
            new_targets: t.List[Target] = []
            for tgt in legacy_project.targets:
                compression: t.Optional[Compression] = None
                braille_mode: t.Optional[BrailleMode] = None
                if tgt.format == "html-zip":
                    format = Format.HTML
                    compression = Compression.ZIP
                elif tgt.format == "webwork-sets":
                    format = Format.WEBWORK
                elif tgt.format == "webwork-sets-zipped":
                    format = Format.WEBWORK
                    compression = Compression.ZIP
                elif tgt.format == "braille-electronic":
                    format = Format.BRAILLE
                    braille_mode = BrailleMode.ELECTRONIC
                elif tgt.format == "braille-emboss":
                    format = Format.BRAILLE
                    braille_mode = BrailleMode.EMBOSS
                else:
                    format = Format(tgt.format.value)
                d = tgt.dict()
                del d["format"]
                # The v2 `output` is a combination of these two v1 fields.
                d["output"] = tgt.output_dir / tgt.output_filename
                # Remove the `None` from optional values, so the new format can replace these.
                for key in ("site", "xsl", "latex_engine"):
                    if d[key] is None:
                        del d[key]
                # Include the braille mode only if it was specified.
                if braille_mode is not None:
                    d["braille_mode"] = braille_mode
                new_target = Target(
                    format=format,
                    compression=compression,
                    **d,
                )
                new_targets.append(new_target)

            # Incorrect from a type perspective, but used to translate from old to new classes.
            legacy_project.targets = new_targets  # type: ignore
            p = Project(
                ptx_version="2",
                _path=_path,
                # Rename from `executables` to `_executables` when moving from the old to new project format.
                _executables=legacy_project.executables,
                # Since there was no `publication` path in the old format, use an empty path. (A nice feature: if all target publication files begin with `publication`, avoid this.)
                publication=Path(""),
                # The same is true for these paths.
                source=Path(""),
                output=Path(""),
                site=Path(""),
                xsl=Path(""),
                **legacy_project.dict(),
            )

        # Set the `_project` for each target, which isn't handled in the XML.
        for _tgt in p.targets:
            _tgt._project = p
            _tgt.post_validate_publication()
        return p

    def new_target(self, name: str, format: str, **kwargs: t.Any) -> None:
        self.targets.append(
            Target(name=name, format=Format(format), _project=self, **kwargs)
        )

    def _get_target(
        self,
        # If `name` is `None`, return the default (first) target; otherwise, return the target given by `name`.
        name: t.Optional[str] = None
        # Returns the target if found, or `None`` if it's not found.
    ) -> t.Optional["Target"]:
        if len(self.targets) == 0:
            # no target to return
            return None
        if name is None:
            # return default target
            return self.targets[0]
        try:
            # return first target matching the provided name
            return next(t for t in self.targets if t.name == name)
        except StopIteration:
            # but no such target was found
            return None

    # Return `True` if the target exists.
    def has_target(
        self,
        # See `name` from `_get_target`.
        name: t.Optional[str] = None,
    ) -> bool:
        return self._get_target(name) is not None

    def get_target(
        self,
        # See `name` from `_get_target`.
        name: t.Optional[str] = None,
    ) -> "Target":
        t = self._get_target(name)
        assert t is not None
        return t

    def abspath(self) -> Path:
        # Since `_path` stores the path to the project file, the parent of this gives the directory it resides in.
        return self._path.parent

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
