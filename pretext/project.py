import pickle
from lxml import etree as ET
from lxml.etree import _Element
import os
import shutil
import logging
import tempfile
from . import utils, generate, core
from . import build as builder
from . import ASSETS
from pathlib import Path
import sys
from .config.xml_overlay import ShadowXmlDocument
from typing import Dict, List, Optional, Tuple
import hashlib

log = logging.getLogger("ptxlogger")

asset_table_type = Dict[Tuple[str, str], bytes]


class Target:
    def __init__(self, xml_element: _Element, project_path: Path):
        # construction is done!
        self.__xml_element = xml_element
        self.__project_path = Path(project_path).resolve()
        # ensure assets directories exist as assumed by core PreTeXt
        if (ex_dir := self.external_dir()) is not None:
            os.makedirs(ex_dir, exist_ok=True)
        if (gen_dir := self.generated_dir()) is not None:
            os.makedirs(gen_dir, exist_ok=True)

    def xml_element(self) -> _Element:
        return self.__xml_element

    def project_path(self) -> Path:
        return self.__project_path

    # Perform basic schema checking of the project file: the given attribute must be present.
    def require_str_value(self, value: Optional[str], err: str) -> str:
        assert value is not None, f"Invalid project file: missing {err}."
        return value

    def require_tag_text(self, tag_name: str) -> str:
        element = self.xml_element().find(tag_name)
        assert element is not None, f"Invalid project file: missing {tag_name} tag."
        return self.require_str_value(element.text, f"{tag_name} contents")

    def name(self) -> str:
        # Targets should have a name attribute.
        return self.require_str_value(
            self.xml_element().get("name"), "name attribute"
        ).strip()

    def pdf_method(self) -> str:
        pdf_method = self.xml_element().get("pdf-method")
        if pdf_method is not None:
            return pdf_method.strip()
        else:
            return "xelatex"  # default

    def format(self) -> str:
        return self.require_tag_text("format").strip()

    def source(self) -> Path:
        return self.project_path() / self.require_tag_text("source").strip()

    def source_dir(self) -> Path:
        return Path(self.source()).parent

    def source_xml(self) -> _Element:
        ele_tree = ET.parse(self.source())
        ele_tree.xinclude()
        return ele_tree.getroot()

    def publication(self) -> Path:
        return self.project_path() / self.require_tag_text("publication").strip()

    def publication_dir(self) -> Path:
        return self.publication().parent

    def publication_rel_from_source(self) -> Path:
        return self.publication().relative_to(self.source_dir())

    def publication_xml(self) -> _Element:
        ele_tree = ET.parse(self.publication())
        ele_tree.xinclude()
        return ele_tree.getroot()

    def external_dir(self) -> Optional[Path]:
        dir_ele = self.publication_xml().find("source/directories")
        if dir_ele is None:
            log.error("Publication file does not specify asset directories.")
            return None
        rel_dir = dir_ele.get("external")
        assert (
            rel_dir is not None
        ), "Invalid project file: missing value in source/directories/external tag."
        return self.source_dir() / rel_dir

    # Like the above function, but asserts if the external directory wasn't found.
    def external_dir_found(self) -> Path:
        ed = self.external_dir()
        assert ed is not None, "Internal error: external directory not found."
        return ed

    def generated_dir(self) -> Optional[Path]:
        dir_ele = self.publication_xml().find("source/directories")
        if dir_ele is None:
            log.error("Publication file does not specify asset directories.")
            return None
        rel_dir = dir_ele.get("generated")
        assert (
            rel_dir is not None
        ), "Invalid project file: missing value in source/directories/generated tag."
        return self.source_dir() / rel_dir

    # Like the above function, but asserts if the external directory wasn't found.
    def generated_dir_found(self) -> Path:
        gd = self.generated_dir()
        assert gd is not None, "Internal error: generated directory not found."
        return gd

    def output_dir(self) -> Path:
        return (
            Path(self.__project_path) / self.require_tag_text("output-dir").strip()
        ).resolve()

    def output_filename(self) -> Optional[str]:
        if self.xml_element().find("output-filename") is None:
            return None
        else:
            return self.require_tag_text("output-filename").strip()

    def port(self) -> int:
        view_ele = self.xml_element().find("view")
        if view_ele is not None and (port := view_ele.get("port")) is not None:
            return int(port)
        else:
            return 8000

    def stringparams(self) -> Dict[str, str]:
        sp = self.xml_element().xpath("stringparam")
        assert isinstance(sp, List), "Project file error: stringparam is empty."
        ret = {}
        for sp_ele in sp:
            assert isinstance(
                sp_ele, _Element
            ), "Project file error: stringparam contents must be key/value pairs."
            key = self.require_str_value(
                sp_ele.get("key"), "Project  file error: stringparam missing key."
            )
            value = self.require_str_value(
                sp_ele.get("value"), "Project  file error: stringparam missing value."
            )
            ret[key.strip()] = value.strip()
        return ret

    def xsl_path(self) -> Optional[Path]:
        if self.xml_element().find("xsl") is not None:
            return (
                Path(self.__project_path) / self.require_tag_text("xsl").strip()
            ).resolve()
        else:
            return None

    def xmlid_root(self) -> Optional[str]:
        ele = self.xml_element().find("xmlid-root")
        if ele is None:
            return None
        else:
            return self.require_str_value(ele.text, "xmlid-root").strip()

    def asset_hash(self) -> asset_table_type:
        asset_hash_dict = {}
        for asset in ASSETS:
            if asset == "webwork":
                ww = self.source_xml().xpath(".//webwork[@*|*]")
                assert isinstance(ww, List)
                # WeBWorK must be regenerated every time *any* of the ww exercises change.
                if len(ww) == 0:
                    # Only generate a hash if there are actually ww exercises in the source
                    continue
                h = hashlib.sha256()
                for node in ww:
                    assert isinstance(node, _Element)
                    h.update(ET.tostring(node))
                asset_hash_dict[(asset, "")] = h.digest()
            elif asset != "ALL":
                # everything else can be updated individually, if it has an xml:id
                source_assets = self.source_xml().xpath(f".//{asset}")
                assert isinstance(source_assets, List)
                if len(source_assets) == 0:
                    # Only generate a hash if there are actually assets of this type in the source
                    continue
                h_no_id = hashlib.sha256()
                for node in source_assets:
                    assert isinstance(node, _Element)
                    # First see if the node has an xml:id, or if it is a child of a node with an xml:id (but we haven't already made this key)
                    if (
                        (id := node.xpath("@xml:id") or node.xpath("parent::*/@xml:id"))
                        and isinstance(id, List)
                        and (asset, id[0]) not in asset_hash_dict
                    ):
                        assert isinstance(id, _Element)
                        asset_hash_dict[(asset, id[0])] = hashlib.sha256(
                            ET.tostring(node)
                        ).digest()
                    # otherwise collect all non-id'd nodes into a single hash
                    else:
                        h_no_id.update(ET.tostring(node))
                asset_hash_dict[(asset, "")] = h_no_id.digest()
        return asset_hash_dict

    def save_asset_table(self, asset_table: asset_table_type) -> None:
        """
        Saves the asset_table to a pickle file in the generated assets directory based on the target name.
        """
        with open(
            self.generated_dir_found().joinpath(f".{self.name()}_assets.pkl"), "wb"
        ) as f:
            pickle.dump(asset_table, f)

    def load_asset_table(self) -> asset_table_type:
        """
        Loads the asset_table from a pickle file in the generated assets directory based on the target name.
        """
        try:
            with open(
                self.generated_dir_found().joinpath(f".{self.name()}_assets.pkl"), "rb"
            ) as f:
                return pickle.load(f)
        except Exception:
            return {}

    def needs_ww_reps(self) -> bool:
        return self.source_xml().find(".//webwork/statement") is not None

    def has_ww_reps(self) -> bool:
        return Path.exists(
            self.generated_dir_found() / "webwork" / "webwork-representations.xml"
        )


class Project:
    def __init__(self, project_path: Optional[Path] = None):
        project_path = project_path or utils.project_path()
        assert project_path is not None, "Unable to find project path."
        xml_element = ET.parse(project_path / "project.ptx").getroot()
        self.__xml_element = xml_element
        self.__project_path = project_path
        # prepre core PreTeXt python scripts
        self.init_ptxcore()

    def apply_overlay(self, overlay: ShadowXmlDocument) -> List[str]:
        """
        Modify the internal data structure of the `project.ptx` XML tree by applying the supplied overlay.
        This modification happens in-memory only.
        """
        return overlay.overlay_tree(self.__xml_element)

    def xml_element(self) -> _Element:
        return self.__xml_element

    def targets(self) -> List[Target]:
        t = self.xml_element().xpath("targets/target")
        assert isinstance(
            t, List
        ), "Project file error: expected list of targets in targets/target tags."
        ret: List[Target] = []
        for target_element in t:
            assert isinstance(t, _Element), "Project file error: target must be a tag."
            t.append(
                Target(xml_element=target_element, project_path=self.__project_path)
            )
        return ret

    def target_names(self, *args: str) -> List[str]:
        # Optional arguments are formats: returns list of targets that have that format.
        names = []
        for target in self.targets():
            if not args or target.format() in args:
                names.append(target.name())
        return names

    def print_target_names(self) -> None:
        for target in self.targets():
            print(target.name())

    def target(self, name: Optional[str] = None) -> Optional[Target]:
        if name is None:
            target_element = self.xml_element().find("targets/target")
        else:
            target_element = self.xml_element().find(f'targets/target[@name="{name}"]')
        if target_element is not None:
            return Target(xml_element=target_element, project_path=self.__project_path)
        else:
            log.error("Unable to find target.")
            return None

    def view(
        self,
        target_name: str,
        access: str,
        port: int,
        watch: bool = False,
        no_launch: bool = False,
    ) -> None:
        target = self.target(target_name)
        if target is None:
            log.error("Unable to find target.")
            return
        directory = target.output_dir()

        if watch:
            watch_directory = target.source_dir()
        else:
            watch_directory = None
        if not target.output_dir().exists():
            log.error(f"The directory `{target.output_dir()}` does not exist.")
            log.error(
                f"Run `pretext view {target.name()} -b` to build your project before viewing."
            )
            return

        def watch_callback() -> None:
            self.build(target_name)

        utils.run_server(
            directory, access, port, watch_directory, watch_callback, no_launch
        )

    def build(self, target_name: str, clean: bool = False) -> None:
        target = self.target(target_name)
        if target is None:
            log.error(f"Target `{target_name}` not found.")
            return
        # Check for xml syntax errors and quit if xml invalid:
        if not self.xml_source_is_valid(target_name):
            return
        if not self.xml_publication_is_valid(target_name):
            return
        # Validate xml against schema; continue with warning if invalid:
        self.xml_schema_validate(target_name)
        if clean:
            # refuse to clean if output is not a subdirectory of the working directory or contains source/publication
            if Path(self.__project_path) not in target.output_dir().parents:
                log.warning(
                    "Refusing to clean output directory that isn't a proper subdirectory of the project."
                )
            elif (
                target.output_dir() in (target.source_dir() / "foo").parents
                or target.output_dir() in (target.publication_dir() / "foo").parents
            ):
                log.warning(
                    "Refusing to clean output directory that contains source or publication files."
                )
            # handle request to clean directory that does not exist
            elif not target.output_dir().exists():
                log.warning(
                    f"Directory {target.output_dir()} already does not exist, nothing to clean."
                )
            else:
                log.warning(
                    f"Destroying directory {target.output_dir()} to clean previously built files."
                )
                shutil.rmtree(target.output_dir())
        # if custom xsl, copy it into a temporary directory (different from the building temporary directory)
        custom_xsl = None
        if (txp := target.xsl_path()) is not None:
            temp_xsl_path = Path(tempfile.mkdtemp())
            log.info(f"Building with custom xsl {txp} specified in project.ptx")
            utils.copy_custom_xsl(txp, temp_xsl_path)
            custom_xsl = temp_xsl_path / txp.name
        # warn if "publisher" is one of the string-param keys:
        if "publisher" in target.stringparams():
            log.warning(
                "You specified a publication file via a stringparam.  This is ignored in favor of the publication file given by the <publication> element in the project manifest."
            )
        log.info(f"Preparing to build into {target.output_dir()}.")
        try:
            if target.format().startswith("html"):
                # html-zip is a special case of html that passes True to the zip parameter
                builder.html(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    custom_xsl,
                    target.xmlid_root(),
                    target.format().startswith("html-zip"),
                )
            elif target.format() == "latex":
                builder.latex(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    custom_xsl,
                )
                # core script doesn't put a copy of images in output for latex builds, so we do it instead here
                shutil.copytree(
                    target.external_dir_found(),
                    target.output_dir() / "external",
                    dirs_exist_ok=True,
                )
                shutil.copytree(
                    target.generated_dir_found(),
                    target.output_dir() / "generated",
                    dirs_exist_ok=True,
                )
            elif target.format() == "pdf":
                builder.pdf(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    custom_xsl,
                    target.pdf_method(),
                )
            elif target.format() == "custom":
                if custom_xsl is None:
                    raise Exception("Must specify custom XSL for custom build.")
                builder.custom(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    custom_xsl,
                    target.output_filename(),
                )
            elif target.format() == "epub":
                builder.epub(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                )
            elif target.format() == "kindle":
                builder.kindle(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                )
            elif target.format() == "braille" or target.format() == "braille-emboss":
                builder.braille(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    page_format="emboss",
                )
            elif target.format() == "braille-electronic":
                builder.braille(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    page_format="electronic",
                )
            elif target.format().startswith("webwork-sets"):
                # webwork-sets-zipped is a special case which will pass True to the zipped parameter.
                builder.webwork_sets(
                    target.source(),
                    target.publication(),
                    target.output_dir(),
                    target.stringparams(),
                    target.format().startswith("webwork-sets-zip"),
                )
            else:
                log.critical(f"The build format {target.format()} is not supported.")
        except Exception as e:
            log.critical(
                f"A fatal error has occurred:\n {e} \nFor more info, run pretext with `-v debug`"
            )
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit(f"Failed to build pretext target {target.format()}.  Exiting...")
        finally:
            # remove temp directories left by core.
            core.release_temporary_directories()
        # build was successful
        log.info(f"\nSuccess! Run `pretext view {target.name()}` to see the results.\n")
        if custom_xsl is not None:
            # errors may occur in Windows so we do the best we can
            shutil.rmtree(custom_xsl.parent, ignore_errors=True)

    def generate(
        self,
        target_name: str,
        asset_list: Optional[List[str]] = None,
        all_formats: bool = False,
        xmlid: Optional[str] = None,
    ) -> None:
        if asset_list is None:
            asset_list = []
            gen_all = True
        else:
            gen_all = False
        target = self.target(target_name)
        if target is None:
            log.error(f"Target `{target_name}` not found.")
            return
        xmlid = xmlid or target.xmlid_root()
        # build targets:
        if gen_all or "webwork" in asset_list:
            webwork_output = target.generated_dir_found() / "webwork"
            generate.webwork(
                target.source(),
                target.publication(),
                webwork_output,
                target.stringparams(),
                xmlid,
            )
        if gen_all or "latex-image" in asset_list:
            generate.latex_image(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                target.format(),
                xmlid,
                target.pdf_method(),
                all_formats,
            )
        if gen_all or "asymptote" in asset_list:
            generate.asymptote(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                target.format(),
                xmlid,
                all_formats,
            )
        if gen_all or "sageplot" in asset_list:
            generate.sageplot(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                target.format(),
                xmlid,
                all_formats,
            )
        if gen_all or "interactive" in asset_list:
            generate.interactive(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                xmlid,
            )
        if gen_all or "youtube" in asset_list:
            generate.youtube(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                xmlid,
            )
            generate.play_button(
                target.generated_dir_found(),
            )
        if gen_all or "codelens" in asset_list:
            generate.codelens(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                xmlid,
            )
        if gen_all or "datafile" in asset_list:
            generate.datafiles(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                xmlid,
            )
        if gen_all or "interactive" in asset_list or "youtube" in asset_list:
            generate.qrcodes(
                target.source(),
                target.publication(),
                target.generated_dir_found(),
                target.stringparams(),
                xmlid,
            )
        # Delete temporary directories left behind by core:
        core.release_temporary_directories()

    def deploy(self, target_name: str, update_source: bool) -> None:
        try:
            import git
            import ghp_import
        except ImportError:
            log.error(
                "Git must be installed to use this feature, but couldn't be found."
            )
            log.error("Visit https://github.com/git-guides/install-git for assistance.")
            return
        target = self.target(target_name)
        if target is None:
            log.error(f"Target `{target_name}` not found.")
            return
        if target.format() != "html":  # redundant for CLI
            log.error("Only HTML format targets are supported.")
            return
        try:
            repo = git.Repo(self.__project_path)
        except git.exc.InvalidGitRepositoryError:  # type: ignore
            log.info("Initializing project with Git.")
            repo = git.Repo.init(self.__project_path)
            try:
                repo.config_reader().get_value("user", "name")
                repo.config_reader().get_value("user", "email")
            except Exception:
                log.info("Setting up name/email configuration for Git...")
                name = input("Type a name to use with Git: ")
                email = input("Type your GitHub email to use with Git: ")
                with repo.config_writer() as w:
                    w.set_value("user", "name", name)
                    w.set_value("user", "email", email)
            repo.git.add(all=True)
            repo.git.commit(message="Initial commit")
            repo.active_branch.rename("main")
            log.info("Successfully initialized new Git repository!")
            log.info("")
        log.info(
            f"Preparing to deploy from active `{repo.active_branch.name}` git branch."
        )
        log.info("")
        if repo.bare or repo.is_dirty() or len(repo.untracked_files) > 0:
            log.info("Changes to project source since last commit detected.")
            if update_source:
                log.info("Add/committing these changes to local Git repository.")
                log.info("")
                repo.git.add(all=True)
                repo.git.commit(message="Update to PreTeXt project source.")
            else:
                log.error("Either add and commit these changes with Git, or run")
                log.error(
                    "`pretext deploy -u` to have these changes updated automatically."
                )
                return
        if not target.output_dir().exists():
            log.error(
                f"No build for `{target.name()}` was found in the directory `{target.output_dir()}`."
            )
            log.error(
                f"Try running `pretext view {target.name()} -b` to build and preview your project first."
            )
            return
        log.info(f"Using latest build located in `{target.output_dir()}`.")
        log.info("")
        try:
            origin = repo.remotes.origin
        except AttributeError:
            log.warning("Remote GitHub repository is not yet configured.")
            log.info("")
            log.info(
                "And if you haven't already, create a remote GitHub repository for this project at:"
            )
            log.info("    https://github.com/new")
            log.info('(Do NOT check any "initialize" options.)')
            log.info(
                'On the next page, copy the URL in the "Quick Setup" section (use HTTPS unless you have SSH setup already).'
            )
            log.info("")
            repourl = input("Paste url here: ").strip()
            repo.create_remote("origin", url=repourl)
            origin = repo.remotes.origin
            log.info(
                "\nFor information about authentication options for github, see: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github\n"
            )
        log.info("Committing your latest build to the `gh-pages` branch.")
        log.info("")
        ghp_import.ghp_import(
            target.output_dir(),
            mesg=f"Latest build of target {target.name()}.",
            nojekyll=True,
        )
        log.info(f"Attempting to connect to remote repository at `{origin.url}`...")
        # log.info("(Your SSH password may be required.)")
        log.info("")
        try:
            repo_user, repo_name = utils.parse_git_remote(origin.url)
            repo_url = f"https://github.com/{repo_user}/{repo_name}/"
            # Set pages_url depending on whether project is base pages for the user or a separate repo
            if "github.io" in repo_name:
                pages_url = f"https://{repo_name}"
            else:
                pages_url = f"https://{repo_user}.github.io/{repo_name}/"
        except Exception:
            log.error(f"Unable to parse GitHub URL from {origin.url}")
            log.error("Deploy unsuccessful")
            return
        try:
            origin.push(refspec=f"{repo.active_branch.name}:{repo.active_branch.name}")
            origin.push(refspec="gh-pages:gh-pages")
        except git.exc.GitCommandError:  # type: ignore
            log.warning(
                f"There was an issue connecting to GitHub repository located at {repo_url}"
            )
            log.info("")
            log.info(
                "If you haven't already, configure SSH with GitHub by following instructions at:"
            )
            log.info(
                "    https://docs.github.com/en/authentication/connecting-to-github-with-ssh"
            )
            log.info("Then try to deploy again.")
            log.info("")
            log.info(f"If `{origin.url}` doesn't match your GitHub repository,")
            log.info(
                "use `git remote remove origin` on the command line then try to deploy again."
            )
            log.info("")
            log.error("Deploy was unsuccessful.")
            return
        log.info("")
        log.info("Latest build successfully pushed to GitHub!")
        log.info("")
        log.info("To enable GitHub Pages, visit")
        log.info(f"    {repo_url}settings/pages")
        log.info("selecting the `gh-pages` branch with the `/ (root)` folder.")
        log.info("")
        log.info("Visit")
        log.info(f"    {repo_url}actions/")
        log.info("to check on the status of your GitHub Pages deployment.")
        log.info("")
        log.info("Your built project will soon be available to the public at:")
        log.info(f"    {pages_url}")

    def xml_source_is_valid(self, target_name: str) -> bool:
        target = self.target(target_name)
        if target is None:
            return False
        return utils.xml_syntax_is_valid(target.source())

    def xml_schema_validate(self, target_name: str) -> bool:
        target = self.target(target_name)
        if target is None:
            return False
        return utils.xml_source_validates_against_schema(target.source())

    def xml_publication_is_valid(self, target_name: str) -> bool:
        target = self.target(target_name)
        if target is None:
            log.error(f"Target `{target_name}` not found.")
            return False
        try:
            publication_xml = ET.parse(target.publication())
            # Would we ever have a publication with xi:include?  Just in case...
            publication_xml.xinclude()
        except Exception as e:
            log.critical(f"Unable to read publication file.  Quitting. {e}")
            log.debug("", exc_info=True)
            return False
        if publication_xml.getroot().tag != "publication":
            log.error(
                f'The publication file {target.publication()} must have "<publication>" as its root element.'
            )
            return False
        return True

    def executables(self) -> Dict[str, str]:
        ret = {}
        exec = self.xml_element().xpath("executables/*")
        assert isinstance(
            exec, List
        ), "Invalid project file: executables tag contents must be tags."
        for ele in exec:
            assert isinstance(
                ele, _Element
            ), "Invalid project file: children of <executables> must be tags."
            key = ele.tag
            value = ele.text
            assert (
                value is not None
            ), "Invalid project file: missing value in <executables> tag."
            ret[key] = value

        return ret

    def init_ptxcore(self) -> None:
        core.set_executables(self.executables())
