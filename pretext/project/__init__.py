import typing as t
from enum import Enum
import hashlib
import logging
import multiprocessing
import shutil
import tempfile
import pickle
from pathlib import Path

from lxml import etree as ET
import pelican  # type: ignore
import pelican.settings  # type: ignore
from pydantic import (
    field_validator,
    model_validator,
    ConfigDict,
    HttpUrl,
    PrivateAttr,
    ValidationInfo,
)
import pydantic_xml as pxml
from pydantic_xml.element.element import SearchMode
from .xml import Executables, LegacyProject, LatexEngine
from .. import constants
from .. import core
from .. import codechat
from .. import utils
from .. import types as pt  # PreTeXt types
from ..resources import resource_base_path
from .. import VERSION


log = logging.getLogger("ptxlogger")


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
class PublicationSubset(
    pxml.BaseXmlModel, tag="publication", search_mode=SearchMode.UNORDERED
):
    external: Path = pxml.wrapped("source/directories", pxml.attr())
    generated: Path = pxml.wrapped("source/directories", pxml.attr())


class BrailleMode(str, Enum):
    EMBOSS = "emboss"
    ELECTRONIC = "electronic"


class Compression(str, Enum):
    ZIP = "zip"


# This class defines the possibilities of the `Target.platform`` attribute.
class Platform(str, Enum):
    # A typical HTML build, meant for self-hosting with no server configuration, features, or assumptions.
    WEB = "web"
    # Build output meant for hosting on a Runestone server.
    RUNESTONE = "runestone"


# Author can specify a method for asymptote generation.
class AsyMethod(str, Enum):
    LOCAL = "local"
    SERVER = "server"


# See `Target.server`.
class ServerName(str, Enum):
    SAGE = "sage"
    # Short for Asymptote.
    ASY = "asy"
    # Possible servers to add: Jing, WeBWorK.


# Allow the author to specify a server instead of a local executable for asset generation. See `Target.server`.
class Server(pxml.BaseXmlModel, tag="server"):
    model_config = ConfigDict(extra="forbid")
    name: ServerName = pxml.attr()
    url: HttpUrl = pxml.attr()


class Target(pxml.BaseXmlModel, tag="target", search_mode=SearchMode.UNORDERED):
    """
    Representation of a target for a PreTeXt project: a specific
    build targeting a format such as HTML, LaTeX, etc.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    # Provide access to the containing project.
    _project: "Project" = PrivateAttr()
    # These two attribute are required; everything else is optional.
    name: str = pxml.attr()
    format: Format = pxml.attr()
    # These attributes have simple validators.
    #
    # A path to the root source for this target, relative to the project's `source` path.
    source: Path = pxml.attr(default=Path("main.ptx"))
    # A path to the publication file for this target, relative to the project's `publication` path. This is mostly validated by `post_validate`.
    publication: Path = pxml.attr(default=None)
    latex_engine: LatexEngine = pxml.attr(
        name="latex-engine", default=LatexEngine.XELATEX
    )
    braille_mode: BrailleMode = pxml.attr(
        name="braille-mode", default=BrailleMode.EMBOSS
    )
    stringparams: t.Dict[str, str] = pxml.element(default={})

    # Specify whether this target should be included in a deployment
    deploy: t.Optional[str] = pxml.attr(name="deploy", default=None)
    # A non-default path to the subdirectory of your deployment where this target will live.
    deploy_dir: t.Optional[Path] = pxml.attr(name="deploy-dir", default=None)

    # Case-check different combos of `deploy` / `deploy-dir`
    def to_deploy(self) -> bool:
        deploy = self.deploy
        if deploy is None:
            # didn't specify `deploy`, so deploy iff there's a `deploy_dir`
            return self.deploy_dir is not None
        else:
            # specified `deploy` attr, so deploy iff choice isn't "no"
            return deploy.lower() != "no"

    # These attributes have complex validators.
    # Note that in each case, since we may not have validated the properties we refer to in values, we should use `values.get` instead of `values[]`.
    #
    # The platform; only valid for an HTML target. See `Platform`. Define this before the other complex validators, since several depend on this value being set.
    platform: t.Optional[Platform] = pxml.attr(
        default=None,
        # Always run this, so we can provide a non-optional value for an HTML target.
        validate_default=True,
    )

    @field_validator("platform")
    @classmethod
    def platform_validator(
        cls, v: t.Optional[Platform], info: ValidationInfo
    ) -> t.Optional[Platform]:
        if info.data.get("format") == Format.HTML:
            # For the HTML format, default to the web platform.
            if v is None:
                return Platform.WEB
        else:
            if v is not None:
                raise ValueError(
                    "Only the HTML format supports the platform attribute."
                )
        return v

    # We validate compression before output_filename to use its value to check if we can have an output_filename.
    compression: t.Optional[Compression] = pxml.attr(default=None)

    # Compression is only supported for HTML and WeBWorK formats.
    @field_validator("compression")
    @classmethod
    def compression_validator(
        cls, v: t.Optional[Compression], info: ValidationInfo
    ) -> t.Optional[Compression]:
        if (
            info.data.get("format") not in (Format.HTML, Format.WEBWORK)
            and v is not None
        ):
            raise ValueError("Only the HTML and WeBWorK formats support compression.")
        if (
            info.data.get("format") == Format.HTML
            and info.data.get("platform") == Platform.RUNESTONE
        ):
            raise ValueError(
                "The HTML format for the Runestone platform does not allow compression."
            )
        return v

    # A path to the output directory for this target, relative to the project's `output` path.
    output_dir: Path = pxml.attr(
        name="output-dir",
        default=None,
        # Make the default value for output be `self.name`. Specifying a `default_factory` won't work, since it's a `@classmethod`. So, use a validator (which has access to the object), replacing `None` with `self.name`.
        validate_default=True,
    )

    @field_validator(
        "output_dir",
        # Run this before Pydantic's validation, since the default value isn't allowed.
        mode="before",
    )
    @classmethod
    def output_dir_validator(cls, v: t.Optional[Path], info: ValidationInfo) -> Path:
        # When the format is Runestone, this is overwritten in `post_validate`. Make sure it's not specified.
        if (
            info.data.get("format") == Format.HTML
            and info.data.get("platform") == Platform.RUNESTONE
            and v is not None
        ):
            raise ValueError("The Runestone format's output-dir must not be specified.")
        return (
            # If the `name` isn't set, then we can't build a valid `output_dir`. However, we want to avoid issuing two validation errors in this case, so supply a dummy name instead, since this name will never be used (this Target won't validate).
            Path(v)
            if v is not None
            else Path(info.data.get("name", "no-name-provided"))
        )

    # A path to the output filename for this target, relative to the `output_dir`. The HTML target cannot specify this (since the HTML output is a directory of files, not a single file.)
    output_filename: t.Optional[str] = pxml.attr(
        name="output-filename", default=None, validate_default=True
    )

    @field_validator("output_filename")
    @classmethod
    def output_filename_validator(
        cls, v: t.Optional[str], info: ValidationInfo
    ) -> t.Optional[str]:
        # See if `output-filename` is allowed.
        if v is not None:
            # uncompressed WeBWorK always produces multiple files, so `output-filename` makes no sense.
            if (
                info.data.get("format") == Format.WEBWORK
                and info.data.get("compression") is None
            ):
                raise ValueError(
                    "The output-filename must not be present when the format is  Webwork."
                )
            # For the HTML format, non-zipped or Runestone output produces multiple files.
            if info.data.get("format") == Format.HTML and (
                info.data.get("platform") == Platform.RUNESTONE
                or info.data.get("compression") is None
            ):
                raise ValueError(
                    "The output-filename must not be present when the format is HTML."
                )

        # Verify that this is just a file name, without any prefixed path.
        assert v is None or Path(v).name == v
        return v

    # The method for generating asymptote files. Overrides the project's `asy_method` if specified.
    asy_method: t.Optional[AsyMethod] = pxml.attr(name="asy-method", default=None)

    # See `Server`. Each server name (`sage`, `asy`) may be specified only once. If specified, the CLI will use the server for asset generation instead of a local executable, unless @asy-method is set to "local". Settings for a given server name here override settings at the project level.
    server: t.List[Server] = pxml.element(default=[])

    @field_validator("server")
    @classmethod
    def server_validator(cls, v: t.List[Server]) -> t.List[Server]:
        # Ensure the names are unique.
        if len(set([server.name for server in v])) != len(v):
            raise ValueError("Server names must not be repeated.")
        return v

    # A path to custom XSL for this target, relative to the project's `xsl` path.
    xsl: t.Optional[Path] = pxml.attr(default=None)

    # If the `format == Format.CUSTOM`, then `xsl` must be defined.
    @field_validator("xsl")
    @classmethod
    def xsl_validator(
        cls, v: t.Optional[Path], info: ValidationInfo
    ) -> t.Optional[Path]:
        if v is None and info.data.get("format") == Format.CUSTOM:
            raise ValueError("A custom format requires a value for xsl.")
        return v

    # Allow specifying `_project` in the constructor. (Since it's private, pydantic ignores it by default).
    def __init__(self, **kwargs: t.Any):
        super().__init__(**kwargs)
        if "_project" in kwargs:
            self._project = kwargs["_project"]
            # Since we now have the project, perform validation.
            self.post_validate()

    # Perform validation which requires the parent `Project` object. This can't be placed in a Pydantic validator, since `self._project` isn't set until after validation finishes. So, this must be manually called after that's done.
    def post_validate(self) -> None:
        # If no publication file is specified, assume either `publication.ptx` (if it exists) or the CLI's template `publication.ptx` (which always exists). If a publication file is specified, ensure that it exists.
        #
        # Select a default publication file if it's not provided.
        if self.publication is None:
            self.publication = Path("publication.ptx")
            # If this publication file doesn't exist, ...
            if not self.publication_abspath().exists():
                # ... then use the CLI's built-in template file.
                # TODO: this is wrong, since the returned path is only valid inside the context manager. Instead, need to enter the context here, then exit it when this class is deleted (also problematic).
                with resource_base_path() / "templates" / "publication.ptx" as self.publication:
                    pass
        # Otherwise, verify that the provided publication file exists. TODO: It is silly to check that all publication files exist.  We warn when they don't.  If the target we are calling has a non-existent publication file, then that error will be caught anyway.
        else:
            p_full = self.publication_abspath()
            if not p_full.exists():
                log.warning(
                    f'The target "{self.name}" has a specified publication file that does not exist: {p_full}'
                )
        # Pass `Project.asy_method` to `Target.asy_method` if it's not specified.
        self.asy_method = self.asy_method or self._project.asy_method

        # Merge `Project.server` with `self.server`; entries in `self.server` take precedence.
        self_server_names = [server.name for server in self.server]
        for server in self._project.server:
            if server.name not in self_server_names:
                self.server.append(server)

        # For the Runestone format, determine the `<document-id>`, which specifies the `output_dir`.
        if self.format == Format.HTML and self.platform == Platform.RUNESTONE:
            # We expect `d_list ==  ["document-id contents here"]`.
            d_list = self.source_element().xpath("/pretext/docinfo/document-id/text()")
            if isinstance(d_list, list):
                if len(d_list) != 1:
                    raise ValueError(
                        "Only one <document-id> is allowed in a PreTeXt document."
                    )
                d = d_list[0]
                assert isinstance(d, str)
                # Use the correct number of `../` to undo the project's `output-dir`, so the output from the build is located in the correct directory of `published/document-id`.
                self.output_dir = Path(
                    f"{'../'*len(self._project.output_dir.parents)}published/{d}"
                )
            else:
                raise ValueError(
                    "The <document-id> must be defined for the Runestone format."
                )

    def source_abspath(self) -> Path:
        return self._project.source_abspath() / self.source

    def source_element(self) -> ET._Element:
        source_doc = ET.parse(self.source_abspath())
        for _ in range(25):
            source_doc.xinclude()
        return source_doc.getroot()

    def publication_abspath(self) -> Path:
        return self._project.publication_abspath() / self.publication

    def output_dir_abspath(self) -> Path:
        return self._project.output_dir_abspath() / self.output_dir

    def output_dir_relpath(self) -> Path:
        return self._project.output_dir / self.output_dir

    def deploy_dir_path(self) -> Path:
        if self.deploy_dir is None:
            return Path(self.name)
        return self.deploy_dir

    def deploy_dir_abspath(self) -> Path:
        return self._project.stage_abspath() / self.deploy_dir_path()

    def deploy_dir_relpath(self) -> Path:
        return self._project.stage / self.deploy_dir_path()

    def deploy_path(self) -> Path:
        if self.output_filename is None:
            return self.deploy_dir_path()
        return self.deploy_dir_path() / self.output_filename

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

    def ensure_asset_directories(self, asset: t.Optional[str] = None) -> None:
        self.external_dir_abspath().mkdir(parents=True, exist_ok=True)
        self.generated_dir_abspath().mkdir(parents=True, exist_ok=True)
        if asset is not None:
            # make directories for each asset type that would be generated from "asset":
            for asset_dir in constants.ASSET_TO_DIR[asset]:
                (self.generated_dir_abspath() / asset_dir).mkdir(
                    parents=True, exist_ok=True
                )

    def ensure_output_directory(self) -> None:
        log.debug(
            f"Ensuring output directory for {self.name}: {self.output_dir_abspath()}"
        )
        self.output_dir_abspath().mkdir(parents=True, exist_ok=True)

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
        """
        Returns a hash table (dictionary) with keys the assets present in the current target's source, each having a value that is a dictionary of xml:ids mapped to the hash of the assets below that xmlid of that type.
        ex: {latex-image: {img1: <hash>, img_another: <hash>}, asymptote: {asy_img_1: <hash>}}.
        """
        asset_hash_dict: pt.AssetTable = {}
        for asset in constants.ASSET_TO_XPATH.keys():
            if asset == "webwork":
                # WeBWorK must be regenerated every time *any* of the ww exercises change.
                ww = self.source_element().xpath(".//webwork[@*|*]")
                assert isinstance(ww, t.List)
                if len(ww) == 0:
                    # Only generate a hash if there are actually ww exercises in the source
                    continue
                asset_hash_dict[asset] = {}
                h = hashlib.sha256()
                for node in ww:
                    assert isinstance(node, ET._Element)
                    h.update(ET.tostring(node).strip())
                asset_hash_dict["webwork"][""] = h.digest()
            else:
                # everything else can be updated individually.
                # get all the nodes for the asset attribute
                source_assets = self.source_element().xpath(
                    constants.ASSET_TO_XPATH[asset]
                )
                assert isinstance(source_assets, t.List)
                if len(source_assets) == 0:
                    # Only generate a hash if there are actually assets of this type in the source
                    continue

                # We will have a dictionary of id's that we will get their own hash:
                asset_hash_dict[asset] = {}
                hash_ids = {}
                for node in source_assets:
                    assert isinstance(node, ET._Element)
                    # assign the xml:id of the youngest ancestor of the node with an xml:id as the node's id (or "" if none)
                    ancestor_xmlids = node.xpath("ancestor::*/@xml:id")
                    assert isinstance(ancestor_xmlids, t.List)
                    id = str(ancestor_xmlids[-1]) if len(ancestor_xmlids) > 0 else ""
                    assert isinstance(id, str)
                    # create a new hash object when id is first encountered
                    if id not in hash_ids:
                        hash_ids[id] = hashlib.sha256()
                    # update the hash with the node's xml:
                    hash_ids[id].update(ET.tostring(node).strip())
                    # and update the value of the hash for that asset/id pair
                    asset_hash_dict[asset][id] = hash_ids[id].digest()
        return asset_hash_dict

    def save_asset_table(self, asset_table: pt.AssetTable) -> None:
        """
        Saves the asset_table to a pickle file in the generated assets directory
        based on the target name.
        """
        with open(self.generated_dir_abspath() / f".{self.name}_assets.pkl", "wb") as f:
            pickle.dump(asset_table, f)

    def ensure_webwork_reps(self) -> None:
        """
        Ensures that the webwork representation file is present if the source contains webwork problems.  This is needed to build or generate other assets.
        """
        if self.source_element().xpath(".//webwork[@*|*]"):
            log.debug("Source contains webwork problems")
            if not (
                self.generated_dir_abspath() / "webwork" / "webwork-representations.xml"
            ).exists():
                log.debug("Webwork representations file does not exist, generating")
                self.generate_assets(
                    requested_asset_types=["webwork"], only_changed=False
                )
            else:
                log.debug("Webwork representations file exists, not generating")
        else:
            log.debug("Source does not contain webwork problems")

    def ensure_play_button(self) -> None:
        try:
            core.play_button(dest_dir=(self.generated_dir_abspath() / "play-button"))
            log.debug("Play button generated")
        except Exception as e:
            log.warning(f"Failed to generate play button: {e}")

    def clean_output(self) -> None:
        # refuse to clean if output is not a subdirectory of the project or contains source/publication
        if self._project.abspath() not in self.output_dir_abspath().parents:
            log.warning(
                "Refusing to clean output directory that isn't a proper subdirectory of the project."
            )
        # handle request to clean directory that does not exist
        elif not self.output_dir_abspath().exists():
            log.warning(
                f"Directory {self.output_dir_abspath()} already does not exist, nothing to clean."
            )
        # destroy the output directory
        else:
            log.warning(
                f"Destroying directory {self.output_dir_abspath()} to clean previously built files."
            )
            shutil.rmtree(self.output_dir_abspath())

    def build(
        self,
        clean: bool = False,
        generate: bool = True,
        xmlid: t.Optional[str] = None,
        no_knowls: bool = False,
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

        # verify that a webwork_representations.xml file exists if it is needed; generated if needed.
        self.ensure_webwork_reps()

        # Generate needed assets unless requested not to.
        if generate:
            self.generate_assets(xmlid=xmlid)

        # Ensure the output directories exist.
        self.ensure_output_directory()

        # Modify stringparams for no_knowls
        if no_knowls:
            self.stringparams["debug.skip-knowls"] = "yes"

        # Proceed with the build
        with tempfile.TemporaryDirectory(prefix="pretext_") as tmp_xsl_str:
            tmp_xsl_path = Path(tmp_xsl_str)
            # if custom xsl, copy it into a temporary directory (different from the building temporary directory)
            if (txp := self.xsl_abspath()) is not None:
                log.info(f"Building with custom xsl {txp}")
                utils.copy_custom_xsl(txp, tmp_xsl_path)
                custom_xsl = tmp_xsl_path / txp.name
            else:
                custom_xsl = None

            # warn if "publisher" is one of the string-param keys:
            if "publisher" in self.stringparams:
                log.warning(
                    "You specified a publication file via a stringparam. "
                    + "This is ignored in favor of the publication file given by the "
                    + "<publication> element in the project manifest."
                )

            log.info(f"Preparing to build into {self.output_dir_abspath()}.")
            # The core expects `out_file` to be the full path, not just a file name, if it's not None.
            out_file = (
                (self.output_dir_abspath() / self.output_filename).as_posix()
                if self.output_filename is not None
                else None
            )
            # The copy allows us to modify string params without affecting the original,
            # and avoids issues with core modifying string params
            stringparams_copy = self.stringparams.copy()
            if self.format == Format.HTML:
                if self.platform == Platform.RUNESTONE:
                    # The validator guarantees this.
                    assert self.compression is None
                    assert self.output_filename is None
                    # This is equivalent to setting `<platform host="runestone">` in the publication file.
                    stringparams_copy.update({"host-platform": "runestone"})
                core.html(
                    xml=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    file_format=self.compression or "html",
                    extra_xsl=custom_xsl,
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                )
                codechat.map_path_to_xml_id(
                    self.source_abspath(),
                    self._project.abspath(),
                    self.output_dir_abspath().as_posix(),
                )
            elif self.format == Format.PDF:
                core.pdf(
                    xml=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    extra_xsl=custom_xsl,
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    method=self.latex_engine,
                )
            elif self.format == Format.LATEX:
                core.latex(
                    xml=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    extra_xsl=custom_xsl,
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                )
                utils.manage_directories(
                    self.output_dir_abspath(),
                    external_abs=self.external_dir_abspath(),
                    generated_abs=self.generated_dir_abspath(),
                )
            elif self.format == Format.EPUB:
                utils.npm_install()
                core.epub(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    math_format="svg",
                    stringparams=stringparams_copy,
                )
            elif self.format == Format.KINDLE:
                utils.npm_install()
                core.epub(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    math_format="kindle",
                    stringparams=stringparams_copy,
                )
            elif self.format == Format.BRAILLE:
                log.warning(
                    "Braille output is still experimental, and requires additional libraries from liblouis (specifically the file2brl software)."
                )
                utils.npm_install()
                core.braille(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    page_format=self.braille_mode,
                    stringparams=stringparams_copy,
                )
            elif self.format == Format.WEBWORK:
                core.webwork_sets(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    tgz=self.compression,
                )
            elif self.format == Format.CUSTOM:
                # Need to add the publication file to string params since xsltproc function doesn't include pubfile.
                stringparams_copy["publisher"] = self.publication_abspath().as_posix()
                core.xsltproc(
                    xsl=custom_xsl,
                    xml=self.source_abspath(),
                    result=out_file,
                    output_dir=self.output_dir_abspath().as_posix(),
                    stringparams=stringparams_copy,
                )
                utils.manage_directories(
                    self.output_dir_abspath(),
                    external_abs=self.external_dir_abspath(),
                    generated_abs=self.generated_dir_abspath(),
                )
            else:
                log.critical(f"Unknown format {self.format}")

    def generate_assets(
        self,
        requested_asset_types: t.Optional[t.List[str]] = None,
        all_formats: bool = False,
        only_changed: bool = True,
        xmlid: t.Optional[str] = None,
        pymupdf: bool = False,
    ) -> None:
        """
        Generates assets for the current target.  Options:
           - requested_asset_types: optional list of which assets to generate (latex-image, sagemath, asymptote, etc).  Default will generate all asset types found in target.
           - all_formats: boolean to decide whether the output format of the assets will be just those that the target format uses (default/False) or all possible output formats for that asset (True).
           - only_changed: boolean.  When True (default), function will only generate assets that have changed since last generation.  When False, all assets will be built (hash table will be ignored).
           - xmlid: optional string to specify the root of the subtree of the xml document to generate assets within.
           - pymupdf: temporary boolean to test alternative image generation with pymupdf instead of external programs.
        """
        # Start by getting the assets that need to be generated for the particular target.  This will either be all of them, or just the asset type that was specifically requested.
        if requested_asset_types is None or "ALL" in requested_asset_types:
            requested_asset_types = list(constants.ASSET_TO_XPATH.keys())
        log.debug(f"Assets generation requested for: {requested_asset_types}.")
        requested_asset_types = [
            asset
            for asset in requested_asset_types
            if asset in constants.ASSETS_BY_FORMAT[self.format]
        ]
        log.debug(
            f"Based on format {self.format}, assets to be generated are: {requested_asset_types}."
        )
        # We always build the asset hash table, even if only_changed=True: this tells us which assets need to be built, and how to update the saved asset hash table at the end of the method.
        # utils.clean_asset_table purges any saved assets that are no longer in the target.
        source_asset_table = self.generate_asset_table()
        saved_asset_table = utils.clean_asset_table(
            self.load_asset_table(), source_asset_table
        )
        log.debug(f"Starting asset table: {source_asset_table}")
        # Throw away any asset types that were not requested:
        source_asset_table = {
            asset: source_asset_table[asset]
            for asset in source_asset_table
            if asset in requested_asset_types
        }
        # Throw away requested assets if they are not in source:
        requested_asset_types = [asset for asset in source_asset_table]
        log.debug(
            f"Based on what is in your source, the assets that will be considered are {requested_asset_types}."
        )
        # For each asset type, we need to keep track of whether to build all of the assets (possibly only below the xml:id given) or generate some one-at-a-time.
        # Cases when we would build all:
        #  1. only_change=False,
        #  2. this is the first time building that asset type (in which case, there will be no instances of that asset in saved_asset_table), or
        #  3. There are lots of assets that have changed (so it would be more efficient to call core once).
        # We first we create a list of asset types that we will generate all instances of
        full_generate = []
        partial_generate = []
        if not only_changed:
            full_generate = requested_asset_types.copy()
        else:
            for asset in requested_asset_types:
                if asset not in saved_asset_table:
                    full_generate.append(asset)
                else:
                    partial_generate.append(asset)
                    # (at least for now, later we might move some of these to full_generate

        # Now we repeatedly pass through the source asset table, and purge any assets that we shouldn't build for any reason.

        # If we limit by xml:id, only look for assets below that id in the source tree
        if xmlid is not None:
            log.debug(f"Limiting asset generation to assets below xml:id={xmlid}.")
            # Keep webwork if only there is a webwork below the xmlid:
            ww_nodes = self.source_element().xpath(f"//*[@xml:id='{xmlid}']//webwork")
            assert isinstance(ww_nodes, t.List)
            if len(ww_nodes) == 0:
                source_asset_table.pop("webwork", None)
            # All other assets: we only need to keep the assets whose id is not above the xmlid (we would have used the xmlid as their id if there wasn't any other xmlid below it):
            # Get list of xml:ids below 'xmlid':
            id_list = self.source_element().xpath(f"//*[@xml:id='{xmlid}']//@xml:id")
            assert isinstance(id_list, t.List)
            # Filter by non-webwork assets whose id is in ID list:
            # Note: if an id = "", that means that no ancestor of that asset had an id, which means that it would not be a child of the xml:id we are subsetting.
            log.debug(f"id list: {id_list}")
            for asset in source_asset_table.copy():
                if asset != "webwork":
                    source_asset_table[asset] = {
                        id: source_asset_table[asset][id]
                        for id in source_asset_table[asset]
                        if id in id_list
                    }
                    if len(source_asset_table[asset]) == 0:
                        source_asset_table.pop(asset, None)
            log.debug(f"Eligible assets are: {source_asset_table}")
            # Prune the list of assets based on what is left
            full_generate = [
                asset for asset in full_generate if asset in source_asset_table
            ]
            partial_generate = [
                asset for asset in partial_generate if asset in source_asset_table
            ]
            log.debug(
                f"Partial generate assets are: {partial_generate}, full generate assets are {full_generate}"
            )

        # TODO: check which assets can be generated based on the user's system (and executables).

        # Now for any asset type in `partial_generate`, we looks for the assets that need to be regenerated because they don't match the previous hash.

        for asset in partial_generate.copy():
            log.debug(
                f"Checking whether any {asset} assets have changed and need to be regenerated."
            )
            source_asset_table[asset] = {
                id: source_asset_table[asset][id]
                for id in source_asset_table[asset]
                if saved_asset_table.get(asset, {}).get(id, None)
                != source_asset_table[asset][id]
            }
            # If there are no assets of that type left, remove it from our list:
            log.debug(f"no {asset} assets have changed.")
            if len(source_asset_table[asset]) == 0:
                partial_generate.remove(asset)
        log.debug(
            f"Assets to be regenerated: all: {full_generate}, partial: {partial_generate}"
        )
        # Create a dictionary with `asset: [ids]` that will be built. For assets that will be built fully, `[ids] = [xmlid]` (where `xmlid` could be `None`)
        assets_to_generate = {}
        for asset in full_generate:
            assets_to_generate[asset] = [xmlid]
        for asset in partial_generate:
            assets_to_generate[asset] = [id for id in source_asset_table[asset]]
        log.debug(f"Assets to be generated: {assets_to_generate}")

        # Now further limit the assets to be built by those that have changed since the last build, if only_changed is true.  Either way create a dictionary of asset: [ids] to be built, where asset:[] means to generate all of them.

        # TODO: check if there are too many individual assets to make generating individually is worthwhile.

        # Now we have the correct list of assets we want to build.
        # We proceed to generate the assets that were requested.
        for asset in assets_to_generate:
            self.ensure_asset_directories(asset)

        # Check if all formats are requested and modify accordingly.
        asset_formats = constants.ASSET_FORMATS[self.format]
        if all_formats:
            for asset in assets_to_generate:
                asset_formats[asset] = ["all"]

        # We will keep track of the assets that were successful to update cache at the end.
        successful_assets: t.List[t.Tuple[str, t.Optional[str]]] = []
        # The copy allows us to modify string params without affecting the original,
        # and avoids issues with core modifying string params
        stringparams_copy = self.stringparams.copy()
        # generate assets by calling appropriate core functions :
        if "webwork" in assets_to_generate:
            try:
                core.webwork_to_xml(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    abort_early=False,
                    dest_dir=(self.generated_dir_abspath() / "webwork").as_posix(),
                    server_params=None,
                )
                successful_assets.append(("webwork", None))
            except Exception as e:
                log.error(
                    "Unable to generate webwork.  If you already have a webwork-representations.xml file, this might result in unpredictable behavior."
                )
                log.warning(e)
                log.debug(e, exc_info=True)
        if "latex-image" in assets_to_generate:
            for id in assets_to_generate["latex-image"]:
                log.debug(f"Generating latex-image assets for {id}")
                try:
                    for outformat in asset_formats["latex-image"]:
                        core.latex_image_conversion(
                            xml_source=self.source_abspath(),
                            pub_file=self.publication_abspath().as_posix(),
                            stringparams=stringparams_copy,
                            xmlid_root=id,
                            dest_dir=self.generated_dir_abspath() / "latex-image",
                            outformat=outformat,
                            method=self.latex_engine,
                            pyMuPDF=pymupdf,
                        )
                    successful_assets.append(("latex-image", id))
                except Exception as e:
                    log.error(f"Unable to generate some latex-image assets:\n {e}")
                    log.debug(e, exc_info=True)
        if "asymptote" in assets_to_generate:
            for id in assets_to_generate["asymptote"]:
                try:
                    for outformat in asset_formats["asymptote"]:
                        core.asymptote_conversion(
                            xml_source=self.source_abspath(),
                            pub_file=self.publication_abspath().as_posix(),
                            stringparams=stringparams_copy,
                            xmlid_root=id,
                            dest_dir=self.generated_dir_abspath() / "asymptote",
                            outformat=outformat,
                            method=self.asy_method,
                        )
                    successful_assets.append(("asymptote", id))
                except Exception as e:
                    log.error(f"Unable to generate some asymptote elements: \n{e}")
                    log.debug(e, exc_info=True)
        if "sageplot" in assets_to_generate:
            for id in assets_to_generate["sageplot"]:
                try:
                    for outformat in asset_formats["sageplot"]:
                        core.sage_conversion(
                            xml_source=self.source_abspath(),
                            pub_file=self.publication_abspath().as_posix(),
                            stringparams=stringparams_copy,
                            xmlid_root=id,
                            dest_dir=self.generated_dir_abspath() / "sageplot",
                            outformat=outformat,
                        )
                    successful_assets.append(("sageplot", id))
                except Exception as e:
                    log.error(f"Unable to generate some sageplot images:\n {e}")
                    log.debug(e, exc_info=True)
        if "interactive" in assets_to_generate:
            # Ensure playwright is installed:
            utils.playwright_install()
            for id in assets_to_generate["interactive"]:
                try:
                    core.preview_images(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=id,
                        dest_dir=self.generated_dir_abspath() / "preview",
                    )
                    successful_assets.append(("interactive", id))
                except Exception as e:
                    log.error(f"Unable to generate some interactive previews: \n{e}")
                    log.debug(e, exc_info=True)
        if "youtube" in assets_to_generate:
            for id in assets_to_generate["youtube"]:
                try:
                    core.youtube_thumbnail(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=id,
                        dest_dir=self.generated_dir_abspath() / "youtube",
                    )
                    successful_assets.append(("youtube", id))
                except Exception as e:
                    log.error(f"Unable to generate some youtube thumbnails: \n{e}")
                    log.debug(e, exc_info=True)
            # youtube also requires the play button.
            self.ensure_play_button()
        if "mermaid" in assets_to_generate:
            for id in assets_to_generate["mermaid"]:
                try:
                    core.mermaid_images(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=id,
                        dest_dir=self.generated_dir_abspath() / "mermaid",
                    )
                    successful_assets.append(("mermaid", id))
                except Exception as e:
                    log.error(f"Unable to generate some mermaid images: \n{e}")
                    log.debug(e, exc_info=True)
        if "codelens" in assets_to_generate:
            for id in assets_to_generate["codelens"]:
                try:
                    core.tracer(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=id,
                        dest_dir=self.generated_dir_abspath() / "trace",
                    )
                    successful_assets.append(("codelens", id))
                except Exception as e:
                    log.error(f"Unable to generate some codelens traces: \n{e}")
                    log.debug(e, exc_info=True)
        if "datafile" in assets_to_generate:
            for id in assets_to_generate["datafile"]:
                log.debug(f"Generating datafile assets for {id}")
                try:
                    core.datafiles_to_xml(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=id,
                        dest_dir=self.generated_dir_abspath() / "datafile",
                    )
                    successful_assets.append(("datafile", id))
                except Exception as e:
                    log.error(f"Unable to generate some datafiles:\n {e}")
                    log.debug(e, exc_info=True)
        # Finally, also generate the qrcodes for interactive and youtube assets:
        # NOTE: we do not currently check for success of this for saving assets to the asset cache.
        if "interactive" in assets_to_generate or "youtube" in assets_to_generate:
            for id in set(
                assets_to_generate.get("interactive", [])
                + assets_to_generate.get("youtube", [])
            ):
                try:
                    core.qrcode(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=id,
                        dest_dir=self.generated_dir_abspath() / "qrcode",
                    )
                except Exception as e:
                    log.error(f"Unable to generate some qrcodes:\n {e}", exc_info=True)
                    log.debug(e, exc_info=True)
        # Delete temporary directories left behind by core:
        try:
            core.release_temporary_directories()
        except Exception as e:
            log.error(
                "Unable to release temporary directories.  Please report this error to pretext-support"
            )
            log.debug(e, exc_info=True)
        # After all assets are generated, update the asset cache:
        log.debug(f"Updated these assets successfully: {successful_assets}")
        for asset_type, id in successful_assets:
            if asset_type not in saved_asset_table:
                saved_asset_table[asset_type] = {}
            if id is None:
                # We have updated all assets of this type, so update all of them in the saved asset table:
                for id in source_asset_table[asset_type]:
                    saved_asset_table[asset_type][id] = source_asset_table[asset_type][
                        id
                    ]
            else:
                if id in source_asset_table.get(asset_type, {}):
                    saved_asset_table[asset_type][id] = source_asset_table[asset_type][
                        id
                    ]
        # Save the asset table to disk:
        self.save_asset_table(saved_asset_table)


class Project(pxml.BaseXmlModel, tag="project", search_mode=SearchMode.UNORDERED):
    """
    Representation of a PreTeXt project: a Path for the project
    on the disk, and Paths for where to build output and maintain a site.

    To create a Project object from a project.ptx file, use the `Project.parse()` method.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ptx_version: t.Literal["2"] = pxml.attr(name="ptx-version", default="2")
    _executables: Executables
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
    # A path, relative to the project directory, prepended to any target's `output_dir`.
    output_dir: Path = pxml.attr(name="output-dir", default=Path("output"))
    # A path to the directory holding a project's landing page(s).
    site: Path = pxml.attr(default=Path("site"))
    # A path to stage files for deployment
    stage: Path = pxml.attr(default=Path("output/stage"))
    # A path, relative to the project directory, prepended to any target's `xsl`.
    xsl: Path = pxml.attr(default=Path("xsl"))
    targets: t.List[Target] = pxml.wrapped(
        "targets", pxml.element(tag="target", default=[])
    )

    # The method for generating asymptote images can be specified at the project level, and overridden at the target level.
    #
    # TODO: why is this optional, if there's a non-optional default? How would it ever be optional if loaded from an XML file?
    asy_method: t.Optional[AsyMethod] = pxml.attr(
        name="asy-method", default=AsyMethod.SERVER
    )

    # See the docs on `Target.server`; they apply here as well.
    server: t.List[Server] = pxml.element(default=[])

    @field_validator("server")
    @classmethod
    def server_validator(cls, v: t.List[Server]) -> t.List[Server]:
        # Ensure the names are unique.
        if len(set([server.name for server in v])) != len(v):
            raise ValueError("Server names must not be repeated.")
        return v

    # This validator sets the `_path`, which is provided in the validation context. It can't be loaded from the XML, since this is metadata about the XML (the location of the file it was loaded from).
    # (It's unclear why the typing of the next line is causing issues.)
    @model_validator(mode="after")
    def set_metadata(self, info: ValidationInfo) -> "Project":
        c = info.context
        p = c and c.get("_path")
        # Only assign the path if a valid path was provided in the context.
        if p:
            self._path = p

        # Load the executables, if possible.
        try:
            e_bytes = (self._path.parent / "executables.ptx").read_bytes()
        except FileNotFoundError:
            # If this isn't found, use the already-set default value.
            self._executables = Executables()
        else:
            self._executables = Executables.from_xml(e_bytes)

        return self

    def __init__(self, **kwargs: t.Any):
        # Don't set them now, since Pydantic will reject this (extra attributes are forbidden in this model).
        deferred = {}
        for key in ("_path", "_executables"):
            if key in kwargs:
                deferred[key] = kwargs.pop(key)

        # Build the model without these "extra" attributes.
        super().__init__(**kwargs)

        # Instead, set them after the model was constructed.
        for key, value in deferred.items():
            setattr(self, key, value)
        self._path = self.validate_path(self._path)

        # Always initialize core when a project is created:
        self.init_core()

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
            ptx_version: t.Optional[str] = pxml.attr(name="ptx-version", default=None)

        p_version_only = ProjectVersionOnly.from_xml(xml_bytes)
        if p_version_only.ptx_version is not None:
            p = Project.from_xml(xml_bytes, context={"_path": _path})
        else:
            legacy_project = LegacyProject.from_xml(_path.read_bytes())
            # Legacy projects didn't specify a base output directory, so we need to move up one level.
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
                d = tgt.model_dump()
                del d["format"]

                # Ensure publication file exists (necessary for v2 validation)
                if not Path(tgt.publication).exists():
                    log.warning(
                        f"Publication file at {tgt.publication} does not exist."
                    )
                    log.warning(f"{tgt.name} will not be available.")
                    continue

                # Remove the `None` from optional values, so the new format can replace these.
                for key in ("deploy_dir", "xsl", "latex_engine"):
                    if d[key] is None:
                        del d[key]

                # Include the braille mode only if it was specified.
                if braille_mode is not None:
                    d["braille_mode"] = braille_mode

                # Convert from old stringparams format to new format.
                d["stringparams"] = {
                    old_stringparam["key"]: old_stringparam["value"]
                    for old_stringparam in d["stringparams"]
                }
                # Build a Target from these transformations.
                new_target = Target(
                    format=format,
                    compression=compression,
                    **d,
                )
                new_targets.append(new_target)

            # Replace the old targets with the new targets.
            d = legacy_project.model_dump()
            d["targets"] = new_targets
            # Rename from `executables` to `_executables` when moving from the old to new project format.
            d["_executables"] = legacy_project.executables
            d.pop("executables")
            p = Project(
                ptx_version="2",
                _path=_path,
                # Since there was no `publication` path in the old format's `<project>` element, use an empty path. (A nice feature: if all target publication files begin with `publication`, avoid this.)
                publication=Path(""),
                # The same is true for these paths.
                source=Path(""),
                output_dir=Path(""),
                site=Path(""),
                xsl=Path(""),
                **d,
            )

        # Set the `_project` for each target, which isn't handled in the XML.
        for _tgt in p.targets:
            _tgt._project = p
            _tgt.post_validate()
        return p

    def new_target(
        self, name: str, format: t.Union[str, Format], **kwargs: t.Any
    ) -> Target:
        t = Target(name=name, format=Format(format), **kwargs)
        # Set this after constructing the Target, since extra attributes are not allowed in this model.
        t._project = self
        t.post_validate()
        self.targets.append(t)
        return t

    def _get_target(
        self,
        # If `name` is `None`, return the default (first) target; otherwise, return the target given by `name`.
        name: t.Optional[str] = None,
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
        log_info_for_none: bool = True,
    ) -> "Target":
        t = self._get_target(name)
        assert t is not None
        if name is None and log_info_for_none:
            log.info(f'Since no target was supplied, we will use "{t.name}".\n')
        return t

    def target_names(self, *args: str) -> t.List[str]:
        # Optional arguments are formats: returns list of targets that have that format.
        names = []
        for target in self.targets:
            if not args or target.format in args:
                names.append(target.name)
        return names

    def abspath(self) -> Path:
        # Since `_path` stores the path to the project file, the parent of this gives the directory it resides in.
        return self._path.parent

    def source_abspath(self) -> Path:
        return self.abspath() / self.source

    def publication_abspath(self) -> Path:
        return self.abspath() / self.publication

    def output_dir_abspath(self) -> Path:
        return self.abspath() / self.output_dir

    def stage_abspath(self) -> Path:
        return self.abspath() / self.stage

    def site_abspath(self) -> Path:
        return self.abspath() / self.site

    def deploy_strategy(
        self,
    ) -> t.Literal["default_target", "pelican_default", "pelican_custom", "static"]:
        if len(self.deploy_targets()) == 0:
            return "default_target"
        if not self.site_abspath().exists():
            return "pelican_default"
        if (self.site_abspath() / "site.ptx").exists():
            return "pelican_custom"
        return "static"

    def xsl_abspath(self) -> Path:
        return self.abspath() / self.xsl

    def server_process(
        self,
        access: t.Literal["public", "private"] = "private",
        port: int = 8128,
    ) -> multiprocessing.Process:
        """
        Returns a process for running a simple local web server
        providing the contents of the output directory.
        """
        # This seems to still work, but now that we don't have a --watch option, using multiprocessing probably isn't necessary.  Consider removing in the future.
        return multiprocessing.Process(
            target=utils.serve_forever,
            args=[self.abspath(), access, port],
        )

    def get_executables(self) -> Executables:
        return self._executables

    def init_core(self) -> None:
        # core does not support None as an executable value, so we must
        # adjust accordingly
        exec_dict = self._executables.model_dump()
        for k in exec_dict:
            if exec_dict[k] is None:
                exec_dict[k] = "None"
        core.set_executables(exec_dict)

    def deploy_targets(self) -> t.List[Target]:
        return [tgt for tgt in self.targets if tgt.to_deploy()]

    def stage_deployment(self) -> None:
        # First empty the stage directory (as long as it is safely in the project directory).
        if (
            self.stage_abspath().exists()
            and self.abspath() in self.stage_abspath().parents
        ):
            shutil.rmtree(self.stage_abspath())
            log.debug("Removed old stage directory")

        # Ensure stage directory exists
        self.stage_abspath().mkdir(parents=True, exist_ok=True)

        strategy = self.deploy_strategy()

        print(f"Staging deployment according to strategy {strategy}")

        if strategy == "default_target":
            target = self.get_target()
            if target is None:
                log.error("Target not found.")
                return
            if not target.output_dir_abspath().exists():
                log.error(
                    f"No build for `{target.name}` was found in the directory `{target.output_dir_abspath()}`."
                )
                log.error(
                    f"Try running `pretext build {target.name}` to build your project first."
                )
                return
            log.info(
                f"Staging latest build located in `{target.output_dir_abspath()}` at `{self.stage_abspath()}`."
            )
            log.info("")
            shutil.copytree(
                target.output_dir_abspath(),
                self.stage_abspath(),
                dirs_exist_ok=True,
            )
        else:
            # Stage all deploy targets
            for target in self.deploy_targets():
                if not target.output_dir_abspath().exists():
                    log.warning(
                        f"No build for `{target.name}` was found in the directory `{target.output_dir_abspath()}`."
                        + f"Try running `pretext build {target.name}` to build this component first."
                    )
                    log.info("Skipping this target for now.")
                else:
                    shutil.copytree(
                        target.output_dir_abspath(),
                        target.deploy_dir_abspath(),
                        dirs_exist_ok=True,
                    )
                    log.info(
                        f"Staging `{target.name}` at `{target.deploy_dir_abspath()}`."
                    )
            # Stage the site. (This is done last to overwrite any files generated by targets.)
            if strategy == "static":
                log.info(
                    f"Staging custom static site located in `{self.site.resolve()}` at `{self.stage_abspath()}`."
                )
                shutil.copytree(
                    self.site.resolve(),
                    self.stage_abspath(),
                    dirs_exist_ok=True,
                )
            else:  # strategy == "pelican_default" or "pelican_custom"
                if strategy == "pelican_custom":
                    log.warning(
                        "Support for customizing websites generated by PreTeXt-CLI is experimental!"
                    )
                    log.warning(
                        "Configurations are subject to change from version-to-version without notice."
                    )
                    log.warning(
                        "Discussion: <https://github.com/PreTeXtBook/pretext-cli/discussions/766>"
                    )
                with tempfile.TemporaryDirectory(prefix="pretext_") as tmp_dir_str:
                    log.info(f"Staging generated site at `{self.stage_abspath()}`.")
                    # set variables
                    config = utils.pelican_default_settings()
                    config["OUTPUT_PATH"] = str(self.stage_abspath())
                    if strategy == "pelican_custom":
                        config["PATH"] = str(self.site_abspath())
                    else:
                        config["PATH"] = tmp_dir_str
                    root = self.deploy_targets()[0].source_element()
                    for title_ele in root.iterdescendants("title"):
                        config["SITENAME"] = title_ele.text
                        break
                    else:
                        config["SITENAME"] = "My PreTeXt Project"
                    for subtitle_ele in root.iterdescendants("subtitle"):
                        config["SITESUBTITLE"] = subtitle_ele.text
                        break
                    for blurb_ele in root.iterdescendants("blurb"):
                        config["PTX_SITE_DESCRIPTION"] = blurb_ele.text
                        break
                    config["PTX_TARGETS"] = [
                        (t.name.capitalize(), t.deploy_path())
                        for t in self.deploy_targets()
                    ]
                    if strategy == "pelican_custom":
                        customization = ET.parse(self.site_abspath() / "site.ptx")
                        customization.xinclude()
                        for child in customization.getroot():
                            config[str(child.tag).upper().replace("-", "_")] = (
                                child.text
                            )
                    pelican.Pelican(pelican.settings.configure_settings(config)).run()  # type: ignore
            log.info(f"Deployment is now staged at `{self.stage_abspath()}`.")

    def deploy(
        self,
        update_source: bool = True,
        stage_only: bool = False,
        skip_staging: bool = False,
    ) -> None:
        if not skip_staging:
            self.stage_deployment()
        if not stage_only:
            utils.publish_to_ghpages(self.stage_abspath(), update_source)

    def generate_boilerplate(
        self,
        skip_unmanaged: bool = True,
        update_requirements: bool = False,
        resources: t.Optional[t.List[str]] = None,
        remove_deprecated: bool = True,
    ) -> None:
        """
        Generates boilerplate files needed/suggested for
        a PreTeXt project. Existing files will be overwritten
        as long as they have a comment confirmed they are managed
        by this library and not the user. If `skip_unmanaged` is
        `False`, unmanaged files will be backed up to a `.bak` file
        and then overwritten.
        """
        if resources is None or len(resources) == 0:
            resources = [resource for resource in constants.PROJECT_RESOURCES]
        if not set(resources) <= set(constants.PROJECT_RESOURCES):
            raise TypeError(
                f"{resources} includes a resource not in {constants.PROJECT_RESOURCES}"
            )
        for resource in resources:
            project_resource_path = (
                self.abspath() / constants.PROJECT_RESOURCES[resource]
            ).resolve()
            if project_resource_path.exists():
                # check if file is unmanaged by PreTeXt
                if (
                    "<!-- Managed automatically by PreTeXt authoring tools -->"
                    not in project_resource_path.read_text()
                ):
                    if skip_unmanaged:
                        continue  # continue on to next resource in resources, not copying anything
                    if resource == "requirements.txt" and not update_requirements:
                        continue  # continue on to next resource in resources, not copying anything
                    backup_resource_path = (
                        project_resource_path.parent
                        / f"{project_resource_path.name}.bak"
                    )
                    shutil.copyfile(project_resource_path, backup_resource_path)
                    log.warning(
                        f"A new {resource} file has been generated at {project_resource_path}."
                    )
                    log.warning(
                        f"Your existing {resource} file has been backed up at {backup_resource_path}."
                    )
            if resource != "requirements.txt":
                with resource_base_path() / "templates" / resource as resource_path:
                    if (
                        not project_resource_path.exists()
                        or resource_path.read_text()
                        != project_resource_path.read_text()
                    ):
                        project_resource_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(resource_path, project_resource_path)
            elif update_requirements:
                requirements_txt = f"# <!-- Managed automatically by PreTeXt authoring tools -->\npretext == {VERSION}\n"
                if (
                    not project_resource_path.exists()
                    or project_resource_path.read_text() != requirements_txt
                ):
                    project_resource_path.write_text(requirements_txt)
            log.info(f"Generated `{project_resource_path}`\n")
        if remove_deprecated:
            for depr_resource in constants.DEPRECATED_PROJECT_RESOURCES:
                project_resource_path = (
                    self.abspath()
                    / constants.DEPRECATED_PROJECT_RESOURCES[depr_resource]
                ).resolve()
                backup_resource_path = (
                    project_resource_path.parent / f"{project_resource_path.name}.bak"
                )
                if project_resource_path.exists():
                    # check if file is unmanaged by PreTeXt
                    if (
                        "<!-- Managed automatically by PreTeXt authoring tools -->"
                        not in project_resource_path.read_text()
                    ):
                        if skip_unmanaged:
                            log.warning(
                                f"Resource f{depr_resource} is deprecated and no longer distributed with PreTeXt-CLI."
                            )
                            continue  # continue on to next resource in resources, not deleting anything
                        # back it up
                        shutil.copyfile(project_resource_path, backup_resource_path)
                        log.warning(
                            f"The deprecated {depr_resource} file has been backed up at {backup_resource_path}."
                        )
                    # delete deprecated resource
                    project_resource_path.unlink()
                    log.warning(
                        f"The deprecated {depr_resource} file has been deleted."
                    )
