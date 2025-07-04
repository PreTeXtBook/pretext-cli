import typing as t
from enum import Enum
import hashlib
import json
import logging
import multiprocessing
import shutil
import tempfile
from pathlib import Path
from functools import partial

from lxml import etree as ET  # noqa: N812

try:
    import pelican  # type: ignore
    import pelican.settings  # type: ignore

    PELICAN_NOT_INSTALLED = False
except ImportError:
    PELICAN_NOT_INSTALLED = True

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
from . import generate
from .. import constants
from .. import core
from .. import codechat
from .. import utils
from .. import types as pt  # PreTeXt types
from .. import resources
from .. import VERSION


# If we want to always spit out log messages to stdout even when this module is imported as a library, we could do so with the following two lines:
# from .. import logger
# log = logger.log

# Otherwise, we just set up the logger here to be used by the CLI.
log = logging.getLogger("ptxlogger")


class Format(str, Enum):
    HTML = "html"
    LATEX = "latex"
    PDF = "pdf"
    EPUB = "epub"
    KINDLE = "kindle"
    BRAILLE = "braille"
    REVEALJS = "revealjs"
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
    SCORM = "scorm"


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

    # Specify whether this target is intended for standalone building
    standalone: t.Optional[str] = pxml.attr(name="standalone", default=None)

    # Check whether a target is standalone
    def is_standalone(self) -> bool:
        standalone = self.standalone
        if standalone is None:
            return False
        return standalone.lower() != "no"

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
    # TODO: add support for revealjs when core supports it.
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
    output_dir: t.Optional[Path] = pxml.attr(
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
    def output_dir_validator(
        cls, v: t.Optional[Path], info: ValidationInfo
    ) -> t.Optional[Path]:
        # When the format is Runestone, this is overwritten in `post_validate`. Make sure it's not specified.
        if (
            info.data.get("format") == Format.HTML
            and info.data.get("platform") == Platform.RUNESTONE
            and v is not None
        ):
            raise ValueError("The Runestone format's output-dir must not be specified.")
        if (
            v is None
            and info.data.get("standalone") is not None
            and info.data.get("standalone") != "no"
        ):
            # If we have a standalone target with no output-dir specified, leave it as None.
            return None
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
                if self.is_standalone():
                    # If the project is standalone, use the publication file for standalone projects.
                    self.publication = (
                        resources.resource_base_path() / "publication.ptx"
                    )
                else:
                    self.publication = (
                        resources.resource_base_path() / "templates" / "publication.ptx"
                    )
                # I didn't understand the todo below, but the above seems to fix it.
                # TODO: this is wrong, since the returned path is only valid inside the context manager. Instead, need to enter the context here, then exit it when this class is deleted (also problematic).
                # with resource_base_path() / "templates" / "publication.ptx" as self.publication:
                # pass
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
                        "Only one `document-id` tag is allowed in a PreTeXt document."
                    )
                # NB as of 2025-04-08, we are no longer setting the output directory automatically for
                # Runestone targets.  This must be managed by the project.ptx file or by a client script.
                # The commented code below is how we used to do this.

                # d = d_list[0]
                # assert isinstance(d, str)
                # # Use the correct number of `../` to undo the project's `output-dir`, so the output from the build is located in the correct directory of `published/document-id`.
                # self.output_dir = Path(
                #    f"{'../'*len(self._project.output_dir.parents)}published/{d}"
                # )
            else:
                raise ValueError(
                    "The `document-id` tag must be defined for the Runestone format."
                )

    def source_abspath(self) -> Path:
        return self._project.source_abspath() / self.source

    def original_source_element(self) -> ET._Element:
        """
        Returns the root element of the original source document without running through pretext assembly.
        """
        source_doc = ET.parse(self.source_abspath())
        for _ in range(25):
            source_doc.xinclude()
        print("Type of source_doc: ", type(source_doc))
        return source_doc.getroot()

    def source_element(self) -> ET._Element:
        """
        Returns the root element for the assembled source, after processing with the "version-only" assembly.
        """
        assembled = core.assembly_internal(
            xml=self.source_abspath(),
            pub_file=self.publication_abspath().as_posix(),
            stringparams=self.stringparams.copy(),
            method="version",
        )
        return assembled.getroot()

    def publication_abspath(self) -> Path:
        return self._project.publication_abspath() / self.publication

    def output_dir_abspath(self) -> Path:
        if self.is_standalone() and self.output_dir is None:
            if self.format == Format.PDF or self.compression == Compression.SCORM:
                # When the output is a single file, use the source abspath() as the output directory.
                return self.source_abspath().parent
            # Otherwise use "filename_targetname" as the output directory.
            return (
                self.source_abspath().parent
                / f"{self.source_abspath().stem}_{self.name}"
            )
        assert self.output_dir is not None
        return self._project.output_dir_abspath() / self.output_dir

    def output_dir_relpath(self) -> Path:
        if self.output_dir is None:
            return self.output_dir_abspath()
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

    def generated_cache_abspath(self) -> Path:
        return self._project.generated_cache_abspath()

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
        Loads the asset table from a json file in the generated assets directory
        based on the target name.
        """
        try:
            with open(
                self.generated_cache_abspath() / f".{self.name}_assets.json", "r"
            ) as f:
                return json.load(f)
        except Exception:
            return {}

    def generate_asset_table(self) -> pt.AssetTable:
        """
        Returns a hash table (dictionary) with keys the asset types present in the current target's *assembled* source, each with value a hash of all the assets of that type.
        ex: {latex-image: <hash>, asymptote: <hash>}.

        NOTE: This is a change in behavior starting in 2.13; previously the keys were dictionaries mapping xml:id's to hashes of individual assets.
        """
        asset_hash_dict: pt.AssetTable = {}
        ns = {"pf": "https://prefigure.org"}
        for asset in constants.ASSET_TO_XPATH.keys():
            # everything else can be updated individually.
            # get all the nodes for the asset attribute (using assembled source)
            source_assets = self.source_element().xpath(
                constants.ASSET_TO_XPATH[asset], namespaces=ns
            )
            assert isinstance(source_assets, t.List)
            if len(source_assets) == 0:
                # Only generate a hash if there are actually assets of this type in the source
                continue
            # We will have a dictionary of id's that we will get their own hash:
            # asset_hash_dict[asset] = {}
            hash = hashlib.sha256()
            for node in source_assets:
                assert isinstance(node, ET._Element)
                hash.update(ET.tostring(node))
            asset_hash_dict[asset] = hash.hexdigest()
        return asset_hash_dict

    def save_asset_table(self, asset_table: pt.AssetTable) -> None:
        """
        Saves the asset_table to a json file in the generated assets directory
        based on the target name.
        """
        with open(
            self.generated_cache_abspath() / f".{self.name}_assets.json", "w"
        ) as f:
            json.dump(asset_table, f)

    def ensure_myopenmath_xml(self) -> None:
        """
        Ensures that the myopenmath xml files are present if the source contains myopenmath exercises.  Needed to generate other "static" assets and targets.
        """
        if self.source_element().xpath(".//myopenmath/@problem"):
            mom_prob_nums = self.source_element().xpath(".//myopenmath/@problem")
            assert isinstance(mom_prob_nums, t.List)
            if not (self.generated_dir_abspath() / "problems").exists():
                log.debug("MyOpenMath directory does not exist, creating")
                (self.generated_dir_abspath() / "problems").mkdir(
                    parents=True, exist_ok=True
                )
            else:
                log.debug("MyOpenMath directory exists, not creating")

            for prob_num in mom_prob_nums:
                assert isinstance(prob_num, str)
                log.debug(f"Checking for MyOpenMath problem {prob_num}")
                if not (
                    self.generated_dir_abspath() / "problems" / f"mom-{prob_num}.xml"
                ).exists():
                    log.debug(
                        f"MyOpenMath problem {prob_num} does not exist, generating"
                    )
                    self.generate_assets(
                        requested_asset_types=["myopenmath"], only_changed=False
                    )
                    # Only need to generate once a single missing file is discovered.
                    break
        else:
            log.debug("Source does not contain myopenmath problems")

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

    def clean_assets(self) -> None:
        for asset_dir in [self.generated_dir_abspath(), self.generated_cache_abspath()]:
            # refuse to clean if generated is not a subdirectory of the project
            if self._project.abspath() not in asset_dir.parents:
                log.warning(
                    "Refusing to clean generated directory that isn't a proper subdirectory of the project."
                )
            # handle request to clean directory that does not exist
            elif not asset_dir.exists():
                log.warning(
                    f"Directory {asset_dir} already does not exist, nothing to clean."
                )
            # destroy the generated directory
            else:
                log.warning(
                    f"Destroying directory {asset_dir} to clean previously built assets."
                )
                shutil.rmtree(asset_dir)

    def build_theme(self) -> None:
        """
        Builds or copies the theme for an HTML-formatted target.
        """
        # if the format of target is not HTML, do nothing with a warning.
        if self.format != Format.HTML:
            log.warning(
                f"Theme building is only supported for HTML targets, not {self.format}."
            )
            return
        # Call the core function to build and/or copy the theme to the output folder
        log.info(f"Building theme for target '{self.name}'")
        utils.ensure_css_node_modules()
        pub_vars = core.get_publisher_variable_report(
            self.source_abspath(),
            self.publication_abspath().as_posix(),
            self.stringparams,
        )
        core.build_or_copy_theme(
            xml=self.source_abspath(),
            pub_var_dict=pub_vars,
            tmp_dir=self.output_dir_abspath().as_posix(),
        )
        log.info(f"Theme built for target '{self.name}'")

    def build(
        self,
        clean: bool = False,
        generate: bool = True,
        xmlid: t.Optional[str] = None,
        no_knowls: bool = False,
    ) -> None:
        # Add cli.version to stringparams.  Use only the major and minor version numbers.
        self.stringparams["cli.version"] = VERSION[: VERSION.rfind(".")]

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
        with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmp_xsl_str:
            # Put the custom xsl in a "cli_xsl" directory inside the temporary directory, so we can create a symlink to core from the temporary directory itself.
            tmp_xsl_path = Path(tmp_xsl_str) / "cli_xsl"
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
                    + "`publication` element in the project manifest."
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
                    if (
                        core.get_platform_host(self.publication_abspath().as_posix())
                        != "runestone"
                    ):
                        log.warning(
                            "The platform host in the publication file is not set to runestone. Since the requested target has @platform='runestone', we will override the publication file's platform host."
                        )
                utils.ensure_css_node_modules()
                core.html(
                    xml=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    file_format=self.compression or "html",
                    extra_xsl=custom_xsl,
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    ext_rs_methods=utils.rs_methods,
                )
                try:
                    codechat.map_path_to_xml_id(
                        self.source_abspath(),
                        self._project.abspath(),
                        self.output_dir_abspath().as_posix(),
                    )
                except Exception as e:
                    log.warning(
                        "Failed to map codechat path to xml id; codechat will not work."
                    )
                    log.debug(f"Error: {e}")
                    log.debug("Traceback:", exc_info=True)
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
                utils.mjsre_npm_install()
                core.epub(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    math_format="svg",
                    stringparams=stringparams_copy,
                )
            elif self.format == Format.KINDLE:
                utils.mjsre_npm_install()
                core.epub(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                    math_format="kindle",
                    stringparams=stringparams_copy,
                )
            elif self.format == Format.REVEALJS:
                core.revealjs(
                    xml=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    file_format=None,
                    extra_xsl=custom_xsl,
                    out_file=out_file,
                    dest_dir=self.output_dir_abspath().as_posix(),
                )
            elif self.format == Format.BRAILLE:
                log.warning(
                    "Braille output is still experimental, and requires additional libraries from liblouis (specifically the file2brl software)."
                )
                utils.mjsre_npm_install()
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
                # Delete temporary directories left behind by core:
        try:
            core.release_temporary_directories()
        except Exception as e:
            log.error(
                "Unable to release temporary directories.  Please report this error to pretext-support"
            )
            log.debug(e, exc_info=True)

    def generate_assets(
        self,
        requested_asset_types: t.Optional[t.List[str]] = None,
        all_formats: bool = False,
        only_changed: bool = True,
        xmlid: t.Optional[str] = None,
        clean: bool = False,
        skip_cache: bool = False,
    ) -> None:
        """
        Generates assets for the current target.  Options:
           - requested_asset_types: optional list of which assets to generate (latex-image, sagemath, asymptote, etc).  Default will generate all asset types found in target.
           - all_formats: boolean to decide whether the output format of the assets will be just those that the target format uses (default/False) or all possible output formats for that asset (True).
           - only_changed: boolean.  When True (default), function will only generate asset types that have changed since last generation.  When False, all assets will be built (hash table will be ignored), althoug cached assets will still be used whenever possible.
           - xmlid: optional string to specify the root of the subtree of the xml document to generate assets within.
        """
        log.info("Generating any needed assets.")

        # clear out the generated assets and cache if requested
        if clean:
            self.clean_assets()

        # Ensure that the generated_cache directories exist:
        for subdir in ["latex-image", "asymptote", "sageplot", "prefigure"]:
            if not (self.generated_cache_abspath() / subdir).exists():
                (self.generated_cache_abspath() / subdir).mkdir(
                    parents=True, exist_ok=True
                )
        log.debug(
            f"Using cached assets in {self.generated_cache_abspath()} where possible."
        )
        # Two "ensure" functions call generate to get just a single asset.  Every generation step other than webwork must have webwork generated, so unless we are "ensuring" webwork, we will need to call ensure webwork.  Note if this function was called with just webwork, then we would move down and actually build webwork.
        if requested_asset_types != ["webwork"]:
            log.debug("Ensuring webwork representations file is present.")
            self.ensure_webwork_reps()
            # We also need to ensure myopenmath for all assets except webwork.  However, if we are generating only myopenmath, we should not ensure myopenmath again.
            if requested_asset_types != ["myopenmath"]:
                log.debug("Ensuring MyOpenMath XML files are present.")
                self.ensure_myopenmath_xml()

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
        # utils.clean_asset_table purges any asset types from the loaded table that are no longer in the target.
        source_asset_table = self.generate_asset_table()
        saved_asset_table = utils.clean_asset_table(
            self.load_asset_table(), source_asset_table
        )
        # log.debug(f"Starting asset table: {source_asset_table}")
        # Keep only asset types that were requested:
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

        # Change as of 2025-01-21: we no longer look for individual assets to generate, so the following logic is much simpler than previously.
        # We just need to decide whether to generate an asset type based on whether the saved asset table has a hash matching that in the source asset table.
        assets_to_generate = []
        if only_changed:
            for asset in requested_asset_types:
                if (
                    asset not in saved_asset_table
                    or saved_asset_table[asset] != source_asset_table[asset]
                ):
                    assets_to_generate.append(asset)
        else:
            assets_to_generate = requested_asset_types
        log.debug(f"Assets to be generated: {assets_to_generate}")

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
        successful_assets: t.List[str] = []
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
                successful_assets.append("webwork")
            except Exception as e:
                log.error(
                    "Unable to generate webwork.  If you already have a webwork-representations.xml file, this might result in unpredictable behavior."
                )
                log.warning(e)
                log.debug(e, exc_info=True)
        if "myopenmath" in assets_to_generate:
            try:
                core.mom_static_problems(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=(self.generated_dir_abspath() / "problems").as_posix(),
                )
                successful_assets.append("myopenmath")
            except Exception as e:
                log.error("Unable to generate MyOpenMath static files.")
                log.warning(e)
                log.debug(e, exc_info=True)
        # The dynamic-subs asset output is required for the subsequent asset generation, so needs to be near the top.
        if "dynamic-subs" in assets_to_generate:
            try:
                core.dynamic_substitutions(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=self.generated_dir_abspath() / "dynamic_subs",
                    ext_rs_methods=utils.rs_methods,
                )
                successful_assets.append("dynamic-subs")
            except Exception as e:
                log.error(
                    f"Unable to extract some dynamic exercise substitutions: \n{e}"
                )
                log.debug(e, exc_info=True)
        if "latex-image" in assets_to_generate:
            try:
                for outformat in asset_formats["latex-image"]:
                    core.latex_image_conversion(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=xmlid,
                        dest_dir=self.generated_dir_abspath() / "latex-image",
                        outformat=outformat,
                        method=self.latex_engine,
                        ext_converter=partial(
                            generate.individual_latex_image,
                            cache_dir=self.generated_cache_abspath(),
                            skip_cache=skip_cache,
                        ),
                        # Note: partial(...) is from functools and allows us to pass the extra arguments cache_dir and skip_cache and still pass the resulting function object to core's conversion function.
                    )
                successful_assets.append("latex-image")
            except Exception as e:
                log.error(f"Unable to generate some latex-image assets:\n {e}")
                log.debug(e, exc_info=True)
        if "asymptote" in assets_to_generate:
            try:
                for outformat in asset_formats["asymptote"]:
                    core.asymptote_conversion(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=xmlid,
                        dest_dir=self.generated_dir_abspath() / "asymptote",
                        outformat=outformat,
                        method=self.asy_method,
                        ext_converter=partial(
                            generate.individual_asymptote,
                            cache_dir=self.generated_cache_abspath(),
                            skip_cache=skip_cache,
                        ),
                    )
                successful_assets.append("asymptote")
            except Exception as e:
                log.error(f"Unable to generate some asymptote elements: \n{e}")
                log.debug(e, exc_info=True)
        if "sageplot" in assets_to_generate:
            try:
                for outformat in asset_formats["sageplot"]:
                    core.sage_conversion(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=xmlid,
                        dest_dir=self.generated_dir_abspath() / "sageplot",
                        outformat=outformat,
                        ext_converter=partial(
                            generate.individual_sage,
                            cache_dir=self.generated_cache_abspath(),
                            skip_cache=skip_cache,
                        ),
                    )
                successful_assets.append("sageplot")
            except Exception as e:
                log.error(f"Unable to generate some sageplot images:\n {e}")
                log.debug(e, exc_info=True)
        if "prefigure" in assets_to_generate:
            try:
                for outformat in asset_formats["prefigure"]:
                    core.prefigure_conversion(
                        xml_source=self.source_abspath(),
                        pub_file=self.publication_abspath().as_posix(),
                        stringparams=stringparams_copy,
                        xmlid_root=xmlid,
                        dest_dir=self.generated_dir_abspath() / "prefigure",
                        outformat=outformat,
                        ext_converter=partial(
                            generate.individual_prefigure,
                            cache_dir=self.generated_cache_abspath(),
                            skip_cache=skip_cache,
                        ),
                    )
                successful_assets.append("prefigure")
            except Exception as e:
                log.error(f"Unable to generate some prefigure images:\n {e}")
                log.debug(e, exc_info=True)
        if "interactive" in assets_to_generate:
            try:
                # Ensure playwright is installed:
                utils.playwright_install()
                core.preview_images(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=self.generated_dir_abspath() / "preview",
                )
                successful_assets.append("interactive")
            except Exception as e:
                log.error(f"Unable to generate some interactive previews: \n{e}")
                log.debug(e, exc_info=True)
        if "youtube" in assets_to_generate:
            try:
                core.youtube_thumbnail(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=self.generated_dir_abspath() / "youtube",
                )
                successful_assets.append("youtube")
            except Exception as e:
                log.error(f"Unable to generate some youtube thumbnails: \n{e}")
                log.debug(e, exc_info=True)
            # youtube also requires the play button.
            self.ensure_play_button()
        if "mermaid" in assets_to_generate:
            try:
                core.mermaid_images(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=self.generated_dir_abspath() / "mermaid",
                )
                successful_assets.append("mermaid")
            except Exception as e:
                log.error(f"Unable to generate some mermaid images: \n{e}")
                log.debug(e, exc_info=True)
        if "codelens" in assets_to_generate:
            try:
                core.tracer(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=self.generated_dir_abspath() / "trace",
                )
                successful_assets.append("codelens")
            except Exception as e:
                log.error(f"Unable to generate some codelens traces: \n{e}")
                log.debug(e, exc_info=True)
        if "datafile" in assets_to_generate:
            try:
                core.datafiles_to_xml(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
                    dest_dir=self.generated_dir_abspath() / "datafile",
                )
                successful_assets.append("datafile")
            except Exception as e:
                log.error(f"Unable to generate some datafiles:\n {e}")
                log.debug(e, exc_info=True)
        # Finally, also generate the qrcodes for interactive and youtube assets:
        # NOTE: we do not currently check for success of this for saving assets to the asset cache.
        if "interactive" in assets_to_generate or "youtube" in assets_to_generate:
            try:
                core.qrcode(
                    xml_source=self.source_abspath(),
                    pub_file=self.publication_abspath().as_posix(),
                    stringparams=stringparams_copy,
                    xmlid_root=xmlid,
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
        # After all assets are generated, update the asset cache (but we shouldn't do this if we didn't generate any assets successfully)
        log.debug(f"Updated these assets successfully: {successful_assets}")
        if len(successful_assets) > 0 and not xmlid:
            # If the build limited by xmlid, then we don't know that all assets of that type were build correctly, so we only do this if not generating a subset.
            for asset_type in successful_assets:
                saved_asset_table[asset_type] = source_asset_table[asset_type]
            # Save the asset table to disk:
            self.save_asset_table(saved_asset_table)
        log.info("Finished generating assets.\n")


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
    # A path, relative to the project directory, for storing cached generated assets
    generated_cache: Path = pxml.attr(default=Path(".cache"))
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
        global_manifest: bool = False,
    ) -> "Project":
        _path = cls.validate_path(path)
        # TODO: nicer errors if these files aren't found.
        xml_bytes = _path.read_bytes()

        # Now that we have read the project manifest into xml_bytes, we can go back to the current working directory in case we are using the global manifest. Note that while validate_path returns a path ending in project.ptx, everything past this ignores that suffix, but does take the parent, so we need to include it.
        if global_manifest:
            _path = cls.validate_path(Path("."))

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
        # if global_manifest:
        #    p._path = Path(".")
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
            # if there is no target matching, check if there is a format
            # that matches. Use that as a backup with a warning
            for target in self.targets:
                if target.format == name:
                    true_name = target.name
                    log.warning(
                        f"Could not find a target '{name}', but found a target '{true_name}' with format='{name}'; using this target."
                    )
                    return target
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

    def generated_cache_abspath(self) -> Path:
        return self.abspath() / self.generated_cache

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
        if (self.site_abspath() / "site.ptx").exists() or (
            self.site_abspath() / "site.json"
        ).exists():
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

    def standalone_targets(self) -> t.List[Target]:
        return [tgt for tgt in self.targets if tgt.is_standalone()]

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

        log.info(f"Staging deployment according to strategy {strategy}")

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
                if PELICAN_NOT_INSTALLED:
                    log.error(
                        "Pelican is not installed. Please install Pelican to use this feature."
                    )
                    return
                if strategy == "pelican_custom":
                    log.warning(
                        "Support for customizing websites generated by PreTeXt-CLI is experimental!"
                    )
                    log.warning(
                        "Configurations are subject to change from version-to-version without notice."
                    )
                    log.warning(
                        "Discussion: https://github.com/PreTeXtBook/pretext-cli/discussions/766"
                    )
                with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmp_dir_str:
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
                        if (self.site_abspath() / "site.ptx").exists():
                            customization = ET.parse(self.site_abspath() / "site.ptx")
                            customization.xinclude()
                            for child in customization.getroot():
                                config[str(child.tag).upper().replace("-", "_")] = (
                                    child.text
                                )
                        else:
                            with open(self.site_abspath() / "site.json") as f:
                                customization = json.load(f)
                            config = {**config, **customization}
                    pelican.Pelican(pelican.settings.configure_settings(config)).run()  # type: ignore
            log.info(f"Deployment is now staged at `{self.stage_abspath()}`.")

    def deploy(
        self,
        update_source: bool = True,
        stage_only: bool = False,
        skip_staging: bool = False,
        no_push: bool = False,
    ) -> None:
        if not skip_staging:
            self.stage_deployment()
        if not stage_only:
            utils.publish_to_ghpages(
                self.stage_abspath(), update_source, no_push=no_push
            )

    def is_git_managed(self) -> bool:
        return (self.abspath() / ".git").exists()

    def update_boilerplate(self, backup: bool = False, force: bool = False) -> None:
        """
        Checks each of the managed files in a project.  If the file matches the
        hash of the default file for the provided version, the file will be updated
        to the newest version.  If it does not match, this means the user modified it.
        In that case, we warn, add a note to the top of the file, and continue.

        The managed files are stored in constants.PROJECT_RESOURCES:
        - project.ptx
        - requirements.txt
        - .gitignore
        - .devcontainer.json
        - .github/workflows/pretext-cli.yml
        - codechat_config.yaml
        """

        for resource in constants.PROJECT_RESOURCES:
            if resource in constants.GIT_RESOURCES and not self.is_git_managed():
                # We don't want git specific files if not in a git repo, so move on.
                continue
            project_resource_path = (
                self.abspath() / constants.PROJECT_RESOURCES[resource]
            ).resolve()
            if force:
                self.add_boilerplate(resource, backup=True)
                log.info(f"Generated resource file {resource}.")
                continue
            if not project_resource_path.exists():
                self.add_boilerplate(resource)
                log.info(f"Generated resource file {resource}.")
                continue
            # Since file already existed, we read its content and check if it is unmodified
            if utils.is_unmodified(resource, project_resource_path.read_bytes()):
                log.info(
                    f"Resource {resource} has not changed since it was originially generated by PreTeXt, so it will be updated to the latest version."
                )
                self.add_boilerplate(resource, backup)
            else:
                log.warning(
                    f"Resource {resource} has been modified since created by PreTeXt and will not be updated.\n"
                )

        for depr_resource in constants.DEPRECATED_PROJECT_RESOURCES:
            project_resource_path = (
                self.abspath() / constants.DEPRECATED_PROJECT_RESOURCES[depr_resource]
            ).resolve()
            if project_resource_path.exists():
                # check if file is unmanaged by PreTeXt
                if utils.is_unmodified(
                    depr_resource,
                    project_resource_path.read_bytes(),
                ):
                    self.remove_boilerplate(depr_resource)
                log.warning(f"The deprecated {depr_resource} file has been deleted.")
        return

    def add_boilerplate(self, resource: str, backup: bool = False) -> None:
        """
        Adds the boilerplate file for the given resource to the project. Unless `backup` is set to `True`, the existing file will be overwritten without making a backup.
        """
        if resource not in constants.PROJECT_RESOURCES:
            raise TypeError(
                f"{resource} is not a resource distributed with PreTeXt-CLI."
            )
        project_resource_path = (
            self.abspath() / constants.PROJECT_RESOURCES[resource]
        ).resolve()
        if project_resource_path.exists() and backup:
            backup_resource_path = (
                project_resource_path.parent / f"{project_resource_path.name}.bak"
            )
            shutil.copyfile(project_resource_path, backup_resource_path)
            log.debug(
                f"Created a backup of the existing {resource} file at {backup_resource_path}."
            )
        # All resources except requirements.txt are copied from templates.  We assume this should be done.
        if resource != "requirements.txt":
            resource_path = resources.resource_base_path() / "templates" / resource
            project_resource_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resource_path, project_resource_path)
            log.debug(f"Generated `{project_resource_path}`\n")
        else:
            # requirements.txt is generated with the latest version of PreTeXt
            requirements_txt = f"# This file was automatically generated with PreTeXt {VERSION}.\npretext == {VERSION}\n"
            project_resource_path.write_text(requirements_txt)
            log.debug(f"Generated `{project_resource_path}`\n")
        return

    def remove_boilerplate(self, resource: str, backup: bool = True) -> None:
        """
        Removes the boilerplate file for the given resource from the project.  By default, a backup file is created.
        """
        # Unlikely we would remove a resource in project_resources, but for future-proofing, we add this check.
        if resource in constants.PROJECT_RESOURCES:
            project_resource_path = (
                self.abspath() / constants.PROJECT_RESOURCES[resource]
            )
        elif resource in constants.DEPRECATED_PROJECT_RESOURCES:
            project_resource_path = (
                self.abspath() / constants.DEPRECATED_PROJECT_RESOURCES[resource]
            ).resolve()
        else:
            raise TypeError(
                f"{resource} is not a resource distributed with PreTeXt-CLI."
            )
        if backup:
            backup_resource_path = (
                project_resource_path.parent / f"{project_resource_path.name}.bak"
            )
            shutil.copyfile(project_resource_path, backup_resource_path)
            log.debug(
                f"Created a backup of the existing {resource} file at {backup_resource_path}."
            )
        project_resource_path.unlink()
        log.debug(f"Removed `{project_resource_path}`\n")
        return

    def generate_boilerplate(
        self,
        skip_unmanaged: bool = True,
        update_requirements: bool = False,
        resources: t.Optional[t.List[str]] = None,
        remove_deprecated: bool = True,
    ) -> None:
        """
        `generate_boilerplate` has been depricated.  Use update_boilerplate instead.
        """
        log.error(
            "the `generate_boilerplate` method has been deprecated.  Will attempt to use `update_boilerplate` instead, but some options are inconsistent."
        )
        self.update_boilerplate(backup=True)
        return
