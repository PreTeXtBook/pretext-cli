import datetime
from hashlib import sha256
import hashlib
import os
from collections.abc import Generator
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
import platform
import re
import shutil
import socketserver
import socket
import subprocess
import logging
import logging.handlers
import psutil
import typing as t
from . import types as pt  # PreTeXt types
from lxml import etree as ET  # noqa: N812
from lxml.etree import _ElementTree, _Element

try:
    import pelican.settings  # type: ignore
except ImportError:
    pass
from typing import Any, cast, List, Optional

from . import core, constants, resources, VERSION

# Get access to logger
log = logging.getLogger("ptxlogger")


@contextmanager
def working_directory(path: Path) -> Generator:
    """
    Temporarily change the current working directory.

    Usage:
    with working_directory(path):
        do_things()   # working in the given path
    do_other_things() # back to original path
    """
    current_directory = Path.cwd()
    os.chdir(path)
    log.debug(f"Now working in directory {path}")
    try:
        yield
    finally:
        os.chdir(current_directory)
        log.debug(f"Successfully changed directory back to {current_directory}")


def manage_directories(
    output_dir: Path,
    external_abs: Optional[Path] = None,
    generated_abs: Optional[Path] = None,
) -> None:
    """
    Copies external and generated directories from absolute paths set in external_abs and generated_abs (unless set to None) into the specified output_dir.
    """
    if external_abs is not None:
        external_dir = os.path.join(output_dir, "external")
        shutil.copytree(external_abs, external_dir, dirs_exist_ok=True)

    if generated_abs is not None:
        generated_dir = os.path.join(output_dir, "generated")
        shutil.copytree(
            generated_abs,
            generated_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("*.pkl"),
        )


# Grabs project directory based on presence of `project.ptx`
def project_path(dirpath: Optional[Path] = None) -> Optional[Path]:
    if dirpath is None:
        dirpath = Path().resolve()  # current directory
    if (dirpath / "project.ptx").is_file():
        # we're at the project root
        return dirpath
    if dirpath.parent == dirpath:
        # cannot ascend higher, no project found
        return None
    else:
        # check parent instead
        return project_path(dirpath=dirpath.parent)


# Like above, but asserts if the project path can't be found.
def project_path_found(dirpath: Optional[Path] = None) -> Path:
    pp = project_path(dirpath)
    assert pp is not None, "Invalid project path"
    return pp


# Install's a default project.ptx manifest in the ~/.ptx/{version} directory if missing
def ensure_default_project_manifest() -> None:
    # Get the path to the default project.ptx manifest
    template_manifest = resources.resource_base_path() / "templates" / "project.ptx"
    # Get the path to the user's default project.ptx manifest
    user_project_manifest = resources.resource_base_path().parent / "project.ptx"
    # If the user's default project.ptx manifest is missing, copy the default project.ptx manifest to the user's default project.ptx manifest
    log.debug(
        f"Checking for user's default project.ptx manifest at {user_project_manifest}"
    )
    if not user_project_manifest.exists():
        shutil.copy(template_manifest, user_project_manifest)
        log.debug(
            "Copied default project.ptx manifest to user's default project.ptx manifest."
        )


def project_xml(dirpath: t.Optional[Path] = None) -> _ElementTree:
    if dirpath is None:
        dirpath = Path.cwd()  # current directory
    pp = project_path(dirpath)
    if pp is None:
        project_manifest = resources.resource_base_path() / "templates" / "project.ptx"
    else:
        project_manifest = pp / "project.ptx"
    return ET.parse(project_manifest)


def requirements_version(dirpath: Optional[Path] = None) -> Optional[str]:
    if dirpath is None:
        dirpath = Path.cwd()  # current directory
    pp = project_path(dirpath)
    if pp is None:
        return None
    try:
        with open(pp / "requirements.txt", "r") as f:
            for line in f.readlines():
                if ("pretext ==" in line) or ("pretextbook ==" in line):
                    return line.split("==")[1].strip()
    except Exception as e:
        log.debug("Could not read `requirements.txt`:")
        log.debug(e)
    return None


def project_xml_string(dirpath: Optional[Path] = None) -> str:
    if dirpath is None:
        dirpath = Path.cwd()  # current directory
    return ET.tostring(project_xml(dirpath), encoding="unicode")


# Returns the pretext directory under home.
def home_path() -> Path:
    return Path.home() / ".ptx"


def hash_path(project_path: Path) -> str:
    return sha256(str(project_path).encode("utf-8")).hexdigest()[:10]


# TODO: is this ever called?
def target_xml(
    alias: t.Optional[str] = None, dirpath: t.Optional[Path] = None
) -> Optional[_Element]:
    if dirpath is None:
        dirpath = Path.cwd()  # current directory
    if alias is None:
        return project_xml().find("targets/target")  # first target
    xpath = f'targets/target[@name="{alias}"]'
    _matches = project_xml().xpath(xpath)
    # Given that this is a project target, narrow the type of the match: ``xpath`` can return a wide variety of results.
    matches = cast(List[_Element], _matches)
    if len(matches) == 0:
        log.info(
            f"No targets with alias {alias} found in project manifest file project.ptx."
        )
        return None
    return matches[0]


# check xml syntax
def xml_syntax_is_valid(xmlfile: Path, root_tag: str = "pretext") -> bool:
    # parse xml
    try:
        source_xml = ET.parse(xmlfile)
        source_xml.xinclude()
        log.debug("XML syntax appears well formed.")
        if source_xml.getroot().tag != root_tag:
            log.error(
                f'The file {xmlfile} does not have "<{root_tag}>" as its root element.  Did you use a subfile as your source?  Check the project manifest (project.ptx).'
            )
            return False
    # check for file IO error
    except IOError:
        raise IOError(f"The file {xmlfile} does not exist")
    # check for XML syntax errors
    except ET.XMLSyntaxError as err:
        log.error("XML Syntax Error caused build to fail:")
        log.error(str(err.error_log))
        return False
    except ET.XIncludeError as err:
        log.error("XInclude Error caused build to fail:")
        log.error(str(err.error_log))
        return False
    return True


def xml_source_validates_against_schema(xmlfile: Path) -> bool:
    # get path to RelaxNG schema file:
    schemarngfile = resources.resource_base_path() / "core" / "schema" / "pretext.rng"

    # Open schemafile for validation:
    relaxng = ET.RelaxNG(file=schemarngfile)

    # Parse xml file:
    source_xml = ET.parse(xmlfile)
    source_xml.xinclude()

    # just for testing
    # ----------------
    # relaxng.validate(source_xml)
    # log = relaxng.error_log
    # print(log)

    # validate against schema
    try:
        relaxng.assertValid(source_xml)
        log.info("PreTeXt source passed schema validation.")
    except ET.DocumentInvalid as err:
        log.debug(
            "PreTeXt document did not pass schema validation; unexpected output may result. See .error_schema.log for hints.  Continuing with build."
        )
        with open(".error_schema.log", "w") as error_log_file:
            error_log_file.write(str(err.error_log))
        return False
    return True


# boilerplate to prevent overzealous caching by preview server, and
# avoid port issues
def binding_for_access(access: t.Literal["public", "private"] = "private") -> str:
    if access == "private":
        return "localhost"
    return "0.0.0.0"


def url_for_access(
    access: t.Literal["public", "private"] = "private", port: int = 8000
) -> str:
    if access == "private":
        if os.environ.get("CODESPACES") == "true":
            return f"https://{os.environ.get('CODESPACE_NAME')}-{port}.{os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN')}"
        else:
            return f"http://localhost:{port}"
    return f"http://{socket.gethostbyname(socket.gethostname())}:{port}"


def serve_forever(
    base_dir: Path,
    access: t.Literal["public", "private"] = "private",
    port: int = 8128,
) -> None:
    binding = binding_for_access(access)

    # Previously we defined a custom handler to prevent caching, but we don't need to do that anymore.  It was causing issues with the _static js/css files inside codespaces for an unknown reason.  Might bring this back in the future.
    # 2024-04-05: try using this again to let Firefox work
    class RequestHandler(SimpleHTTPRequestHandler):

        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, directory=base_dir.as_posix(), **kwargs)

        """HTTP request handler with no caching"""

        def end_headers(self) -> None:
            self.send_my_headers()
            SimpleHTTPRequestHandler.end_headers(self)

        def send_my_headers(self) -> None:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")

    class TCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    looking_for_port = True
    while looking_for_port:
        try:
            with TCPServer((binding, port), RequestHandler) as httpd:
                looking_for_port = False
                httpd.serve_forever()
        except OSError:
            log.warning(f"Port {port} could not be used.")
            port += 1
            log.warning(f"Trying port {port} instead.\n")


def start_codespace_server(
    access: t.Literal["public", "private"] = "private",
    port: int = 8128,
) -> None:
    """
    Temporary hack until we can figure out what is going on with codespaces an the (possibly more robust) server process we usually define.
    """
    subprocess.Popen(
        f"python -m http.server {port}",
        shell=True,
    )
    return


# Info on namespaces: http://lxml.de/tutorial.html#namespaces
NSMAP = {
    "xi": "http://www.w3.org/2001/XInclude",
    "xml": "http://www.w3.org/XML/1998/namespace",
}


def nstag(prefix: str, suffix: str) -> str:
    return "{" + NSMAP[prefix] + "}" + suffix


def copy_custom_xsl(xsl_path: Path, output_dir: Path) -> None:
    """
    Copy relevant files that share a directory with `xsl_path`.
    Pre-processing the `.xsl` files to point to subdirectory for graceful deprecation.
    """
    xsl_dir = xsl_path.parent.resolve()
    output_dir = output_dir.resolve()
    log.debug(f"Copying all files in {xsl_dir} to {output_dir}")
    shutil.copytree(xsl_dir, output_dir, dirs_exist_ok=True)
    log.debug(f"Copying core XSL to {output_dir}/core")
    shutil.copytree(
        resources.resource_base_path() / "core" / "xsl", output_dir / "core"
    )
    # Create a symlink to the {output_dir}/core from the parent of the output_dir
    # This supports custom xsl that includes "../xsl" instead of "./core".
    try:
        symlink = output_dir.parent / "xsl"
        if symlink.exists():
            symlink.unlink()
        symlink.symlink_to(output_dir / "core")
    except Exception as e:
        # If the symlink fails, likely because of a Window's permission problem, we just make a second copy.
        log.debug(f"Could not create symlink to {output_dir}/core")
        log.debug(e)
        log.debug("Copying core XSL to {symlink} instead.")
        shutil.copytree(resources.resource_base_path() / "core" / "xsl", symlink)


def check_executable(exec_name: str) -> Optional[str]:
    try:
        exec_cmd = core.get_executable_cmd(exec_name)[0]
        log.debug(f"PTX-CLI: Executable command {exec_name} found at {exec_cmd}")
        return exec_cmd
    except OSError as e:
        log.debug(e)
        return None


def check_asset_execs(element: str, outformats: Optional[List[str]] = None) -> None:
    # outformats is assumed to be a list of formats.
    if outformats is None:
        outformats = []
    # Note that asymptote is done via server, so doesn't require asy.  We could check for an internet connection here for that and webwork, etc.
    log.debug(f"trying to check assets for {element} and output format {outformats}")
    # Create list of executables needed based on output format
    required_execs = []
    if element == "latex-image":
        required_execs = ["xelatex"]
        if "svg" in outformats or "all" in outformats:
            required_execs.append("pdfsvg")
        if "png" in outformats or "all" in outformats:
            required_execs.append("pdfpng")
        if "eps" in outformats or "all" in outformats:
            required_execs.append("pdfeps")
    if element == "sageplot":
        required_execs = ["sage"]
    install_hints = {
        "xelatex": {
            "Windows": "See https://pretextbook.org/doc/guide/html/windows-cli-software.html",
            "Darwin": "",
            "Linux": "",
        },
        "pdfsvg": {
            "Windows": "Follow the instructions at https://pretextbook.org/doc/guide/html/section-installing-pdf2svg.html to install pdf2svg",
            "Darwin": "",
            "Linux": "You should be able to install pdf2svg with your package manager (e.g., `sudo apt install pdf2svg`.  See https://github.com/dawbarton/pdf2svg#pdf2svg.",
        },
        "pdfpng": {
            "Windows": "See https://pretextbook.org/doc/guide/html/windows-cli-software.html",
            "Darwin": "",
            "Linux": "",
        },
        "pdfeps": {
            "Windows": "See https://pretextbook.org/doc/guide/html/windows-cli-software.html",
            "Darwin": "",
            "Linux": "",
        },
        "sage": {
            "Windows": "See https://doc.sagemath.org/html/en/installation/index.html#windows",
            "Darwin": "https://doc.sagemath.org/html/en/installation/index.html#macos",
            "Linux": "See https://doc.sagemath.org/html/en/installation/index.html#linux",
        },
        "pageres": {
            "Windows": "See https://pretextbook.org/doc/guide/html/windows-cli-software.html",
            "Darwin": "",
            "Linux": "",
        },
    }
    for required_exec in required_execs:
        if check_executable(required_exec) is None:
            log.warning(
                f"In order to generate {element} into formats {outformats}, you must have {required_exec} installed, but this appears to be missing or configured incorrectly in pretext.ptx"
            )
            # print installation hints based on operating system and missing program.
            log.info(install_hints[required_exec][platform.system()])


def clean_asset_table(
    dirty_table: pt.AssetTable, clean_table: pt.AssetTable
) -> pt.AssetTable:
    """
    Removes any assets from the dirty_table that are not in the clean_table.
    """
    # Purge any asset types that are no longer in the clean table:
    dirty_table = {
        asset: dirty_table[asset] for asset in dirty_table if asset in clean_table
    }
    # Then purge ids of assets that no longer exist in the clean table:
    # for asset in dirty_table:
    #    dirty_table[asset] = {
    #        id: dirty_table[asset][id]
    #        for id in dirty_table[asset]
    #        if id in clean_table[asset]
    #    }
    return dirty_table


def cannot_find_project(task: str) -> bool:
    """
    Standard messages to be displayed when no project.ptx is found, customized by the "task" to be preformed.
    """
    if project_path() is None:
        log.critical(
            f"Before you can {task} your PreTeXt project, you must be in a (sub)directory initialized with a project.ptx manifest."
        )
        log.critical(
            "Move to such a directory, use `pretext new` to create a new project, or `pretext init` to update existing project for use with the CLI."
        )
        return True
    return False


def show_target_hints(
    target_format: Optional[str],
    # TODO: the type is ``project.Project``, but we can't ``import project`` due to circular imports.
    project: Any,
    task: str,
) -> None:
    """
    This will give the user hints about why they have provided a bad target and make helpful suggestions for them to fix the problem.  We will only run this function when the target_name is not the name in any target in project.ptx.
    """
    # just in case this was called in the wrong place:
    if project.has_target(name=target_format):
        return
    # Otherwise continue with hints:
    if target_format is None:
        log.critical(
            f"No viable targets found in project.ptx.  The available targets are named: {project.target_names()}."
        )
        return
    log.critical(
        f'There is not a target named "{target_format}" for this project.ptx manifest.'
    )
    if target_format in constants.FORMATS:
        target_names = project.target_names(target_format)
        if len(target_names) == 1:
            log.info(
                f'However, the target named "{target_names[0]}" has "{target_format}" as its format.  Try to {task} that instead or edit your project.ptx manifest.'
            )
        elif len(target_names) > 1:
            log.info(
                f'However, the targets with names {target_names} have "{target_format}" as their format.  Try to {task} one of those instead or edit your project.ptx manifest.'
            )
        if target_format in ["epub", "kindle"]:
            log.info(
                f"Instructions for setting up a target with the {target_format} format, including the external programs required, can be found in the PreTeXt guide: https://pretextbook.org/doc/guide/html/epub.html"
            )
    else:
        log.info(
            f"The available targets to {task} are named: {project.target_names()}.  Try to {task} on of those instead or edit your project.ptx manifest."
        )


def mjsre_npm_install() -> None:
    with working_directory(
        resources.resource_base_path() / "core" / "script" / "mjsre"
    ):
        log.info("Attempting to install/update required node packages.")
        try:
            subprocess.run("npm install", shell=True)
        except Exception as e:
            log.critical(
                "Unable to install required npm packages.  Please see the documentation."
            )
            log.critical(e)
            log.debug("", exc_info=True)


def ensure_css_node_modules() -> None:
    # Look for node_modules and install if we can.
    with working_directory(
        resources.resource_base_path() / "core" / "script" / "cssbuilder"
    ):
        # Make sure node version is at least 18:
        try:
            node_cmd = shutil.which("node")
            if node_cmd is None:
                log.warning(
                    "Node.js must be installed to build CSS files.  Please install node.js and npm.\n Will try to use prebuilt CSS files instead."
                )
                raise FileNotFoundError
            node_version = subprocess.run([node_cmd, "-v"], capture_output=True)
            log.debug(f"Node version: {node_version.stdout.decode()}")
            if int(node_version.stdout.decode().split(".")[0][1:]) < 18:
                log.warning(
                    "Node version must be at least 18 to build CSS files.  Please update node.js and npm.\n Will try to use prebuilt CSS files instead."
                )
                return
        except Exception as e:
            log.debug(e)
            log.debug("", exc_info=True)
        # Check if node_modules is already present:
        if Path("node_modules").exists():
            log.debug("Node modules already installed.")
            return
        # If not, try to install them:
        log.debug(
            "Attempting to install/update required node packages to generate css from sass."
        )
        try:
            npm_cmd = shutil.which("npm")
            if npm_cmd is None:
                log.warning(
                    "Cannot find npm.  Will try to use prebuilt CSS files instead."
                )
                raise FileNotFoundError
            subprocess.run([npm_cmd, "install", "--engine-strict=true"])
        except Exception as e:
            log.warning(
                "Unable to install npm packages to build css files.  Non-default CSS themes require node.js and npm to be installed.  See https://pretextbook.org/doc/guide/html/node-and-npm.html"
            )
            log.warning(e)
            log.debug("", exc_info=True)


def playwright_install() -> None:
    """
    Run `playwright install` to ensure that its required browsers and tools are available to it.
    """
    try:
        log.info("Checking for update for required playwright chromium browser.")
        # subprocess.run("playwright install-deps", shell=True)
        subprocess.run("playwright install chromium", shell=True)
        log.debug("Installed dependencies to capture interactive previews")
    except Exception as e:
        log.critical(
            "Unable to install required playwright packages.  Please see the documentation."
        )
        log.critical(e)
        log.debug("", exc_info=True)


def remove_path(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink()  # remove the file
    elif path.is_dir():
        shutil.rmtree(path)  # remove dir and all it contains


def has_errors(mh: logging.handlers.MemoryHandler) -> bool:
    """
    Checks to see if anything (errors etc.) is in the memory handler.
    """
    return len(mh.buffer) > 0


def exit_command(mh: logging.handlers.MemoryHandler) -> None:
    """
    Clean up at the end of a run.
    Reports that there are errors before the handler gets flushed, then exits with errors.
    Otherwise, logs a blank line.
    """
    if has_errors(mh):
        log.info("\n----------------------------------------------------")
        log.info("While running pretext, the following errors occurred:\n")
        log.info(
            "(see log messages above or in the 'logs' folder for more information)"
        )
        mh.flush()
        log.info("----------------------------------------------------")
        raise SystemExit(1)
    else:
        log.debug("Completed without errors.")
        log.info("")


def format_docstring_as_help_str(string: str) -> str:
    """
    Formats a docstring so that it is suitable to pass in as a help string
    in the `click` library.

    Specifically, this function removes leading whitespace and single newlines.
    However, double newlines are preserved.
    """
    import re

    lines = (re.sub(r"\s+", " ", line).strip() for line in string.splitlines())
    return " ".join(line if line else "\n\n" for line in lines)


def parse_git_remote(string: str) -> t.List[str]:
    """
    Given a Git remote such as
    git@github.com:PreTeXtBook/pretext-cli.git or
    https://github.com/PreTeXtBook/pretext-cli.git or
    https://github.com/PreTeXtBook/pretext-cli
    return a list with the username (PreTeXtBook) and reponame (pretext-cli).
    """
    repo_info = list(filter(None, re.split(r"\/|\:|\.git$", string)))
    return repo_info[-2:]


def publish_to_ghpages(directory: Path, update_source: bool) -> None:
    """
    Publish the current project to GitHub pages.
    """
    # Try to import git.repo and ghp_import to make sure git is installed.
    # These need to be done here, because if git is not installed, then this will break,
    # and not everyone will need deploy functionality.
    try:
        import git.repo
        import git.exc
        import ghp_import
    except ImportError:
        log.error("Git must be installed to use this feature, but couldn't be found.")
        log.error("Visit https://github.com/git-guides/install-git for assistance.")
        raise ImportError

    try:
        repo = git.repo.Repo(project_path())
    except git.exc.InvalidGitRepositoryError:
        log.info("Initializing project with Git.")
        repo = git.repo.Repo.init(project_path())
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
    log.info(f"Preparing to deploy from active `{repo.active_branch.name}` git branch.")
    log.info("")
    if repo.bare or repo.is_dirty() or len(repo.untracked_files) > 0:
        log.info("Changes to project source since last commit detected.")
        if update_source:
            log.info("Add/committing these changes to local Git repository.")
            log.info("")
            repo.git.add(all=True)
            repo.git.commit(message="Update to PreTeXt project source.")
            # Should we push this commit?
        else:
            log.warning(
                "Don't forget to either add and commit the changes to your source with git, or run `pretext deploy -u` to have these changes updated automatically."
            )
            log.warning(
                "Just deploying your built project will not save changes to your source on GitHub.`"
            )
            # Note, we no longer return here; continue with deployment even though repo isn't clean.

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
            'On the next page, copy the "HTTPS" version of the URL in the "Quick Setup" section.'
        )
        log.info("")
        repourl = input("Paste url here: ")
        username = repourl.split("/")[-2]
        reponame = repourl.split("/")[-1]
        log.info("")
        log.info("Next, set up a GitHub personal access token. Instructions:")
        log.info(
            "    https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic"
        )
        log.info(
            "Be sure to check the `repo` and `workflow` scopes when generating this token."
        )
        log.info("")
        pat = input("Paste your personal access token (`ghp_RANDOMCHARCTERS`): ")
        log.info("")
        repourl = f"https://{username}:{pat}@github.com/{username}/{reponame}"
        repo.create_remote("origin", url=repourl)
        origin = repo.remotes.origin
    log.info("Committing your latest build to the `gh-pages` branch.")
    log.info("")
    # Should we let ghp_import do the push for us?
    # Should we remove the history?
    ghp_import.ghp_import(
        directory,
        mesg="Latest build deployed.",
        nojekyll=True,
    )
    log.info(f"Attempting to connect to remote repository at `{origin.url}`...")
    # log.info("(Your SSH password may be required.)")
    log.info("")
    try:
        repo_user, repo_name = parse_git_remote(origin.url)
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
            "Make sure you have set up authentication for GitHub.  For more information, visit:"
        )
        log.info("    https://docs.github.com/en/authentication")
        log.info(
            "Make sure you can push changes, either from the command line or in VS Code.  Then try to deploy again."
        )
        log.info("")
        log.info(f"(If `{origin.url}` doesn't match your GitHub repository,")
        log.info(
            "use `git remote remove origin` on the command line then try to deploy again.)"
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


def active_server_port() -> t.Optional[int]:
    """
    Check if a pretext-view server is running already, and if so, return its port number.
    """
    # We look at all currently running processes and check if any are a pretext process that is a child of a pretext process.  This would only happen if we have run a `pretext view` command to start the server, so we can assume that this is the server we are looking for.
    for proc in psutil.process_iter():
        if proc is None:
            continue
        if is_pretext_proc(proc):  # type: ignore
            log.debug(f"Found pretext server running with pid {proc.pid}")
            # Sometimes the process stops but doesn't get removed from the process list.  We check if the process is still running by checking its status.
            if proc.status() not in [psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING]:
                log.debug("Server is stopped.")
                return None
            # To get the port number, we look at the connections the process has open.  We assume that the server is running on the first port that is open.
            try:
                port = proc.connections()[0].laddr.port
                log.debug(f"Server is running on port {port}")
                return port
            except Exception as e:
                log.debug(f"Could not get port number. Exception: {e}", exc_info=True)
    log.debug("No pretext server found running.")
    return None


def stop_server(port: t.Optional[int] = None) -> None:
    """
    Terminate a server running in the background.
    """
    # If a port was passed, we look for a "pretext" process that has a connection on that port, and kill it if we find it.
    if port is not None:
        log.debug(f"Terminating server running on port {port}")
        for proc in psutil.process_iter():
            if len(proc.connections()) > 0:
                if (
                    proc.name() == "pretext"
                    and proc.parent().name() == "pretext"  # type: ignore
                    and proc.connections()[0].laddr.port == port
                ):
                    log.debug(
                        f"Terminating process with PID {proc.pid} hosting on port {port}"
                    )
                    proc.terminate()
    else:
        # As before, we look for a pretext process that is a child of a pretext process.  This time we terminate that process.
        for proc in psutil.process_iter():
            if is_pretext_proc(proc):
                log.debug(f"Terminating process with PID {proc.pid}")
                proc.terminate()


def pelican_default_settings() -> t.Dict[str, t.Any]:
    config = pelican.settings.DEFAULT_CONFIG
    config["THEME"] = resources.resource_base_path() / "pelican" / "ptx-theme"
    config["RELATIVE_URLS"] = True
    config["TIMEZONE"] = "Etc/UTC"
    config["ARTICLE_PATHS"] = ["updates"]
    config["ARTICLE_URL"] = "updates/{date:%Y%m%d}-{slug}/"
    config["ARTICLE_SAVE_AS"] = config["ARTICLE_URL"] + "index.html"
    config["PAGE_PATHS"] = ["pages"]
    config["PAGE_URL"] = "{slug}/"
    config["PAGE_SAVE_AS"] = config["PAGE_URL"] + "index.html"
    config["FEED_ALL_ATOM"] = None
    config["CATEGORY_FEED_ATOM"] = None
    config["TRANSLATION_FEED_ATOM"] = None
    config["AUTHOR_FEED_ATOM"] = None
    config["AUTHOR_FEED_RSS"] = None
    config["STATIC_PATHS"] = ["images", "static"]
    # for now, all PTX_ custom settings are strings (due to use of XML)
    config["PTX_SHOW_TARGETS"] = "yes"
    return config


def latest_version() -> t.Optional[str]:
    """
    Get the latest version of the pretext package from PyPI.
    """
    import requests

    url = "https://pypi.org/pypi/pretext/json"
    try:
        response = requests.get(url, timeout=1)  # 1 second timeout; not critical.
        return response.json()["info"]["version"]
    except Exception as e:
        log.debug("Could not determine latest version of pretext.")
        log.debug(e, exc_info=True)
        return None


def is_earlier_version(v1: str, v2: str) -> bool:
    """
    Check if version v1 is earlier than version v2.
    """
    v1_parts = v1.split(".")
    v2_parts = v2.split(".")
    for i in range(min(len(v1_parts), len(v2_parts))):
        if int(v1_parts[i]) < int(v2_parts[i]):
            return True
        if int(v1_parts[i]) > int(v2_parts[i]):
            return False
    # The only way the first three digits would be equal but the strings would not be equal is if the longer was
    # a pre-release, such as 2.11.5.dev... vs 2.11.5.  In this case, the shorter is the later version.
    if len(v1_parts) < len(v2_parts):
        return True
    # If the lengths are equal, then the versions are equal.
    return False


def check_for_updates() -> None:
    """
    Check if the installed version of pretext is the latest version.
    This is done at most once per day.
    """
    # check whether we have looked for updates today
    last_check = resources.resource_base_path() / "last_update_check.txt"
    if last_check.exists():
        with open(last_check, "r") as f:
            last_date = f.read()
        if last_date == str(datetime.date.today()):
            log.debug("Already checked for updates today.")
            return
    # Check for updates
    current_version = VERSION
    latest = latest_version()
    if latest is None:
        log.debug("Could not check for updates.")
        return
    if is_earlier_version(current_version, latest):
        log.info(
            f"Version {latest} of pretext is available.  You are currently using version {current_version}.\n"
        )
        log.info("To upgrade, run `pretext upgrade`.")
    elif "dev" in current_version:
        log.warning(
            f"You are using a nightly release, {current_version}.  The latest stable release is {latest}.\n"
        )
    else:
        log.info(f"You are using the latest version of pretext, {current_version}.\n")
    # update the last check date
    with open(last_check, "w") as f:
        f.write(str(datetime.date.today()))


def is_pretext_proc(proc: psutil.Process) -> bool:
    if proc.name() == "pretext":
        return False
    parent = proc.parent()
    return parent is not None and parent.name() == "pretext"


def is_unmodified(
    resource: str,
    contents: bytes,
    resource_hash_table: Any = resources.get_resource_hash_table(),
) -> bool:
    """
    Check if a resource file with `contents` has been modified compared to the hash in `resource_hash_table`.  If the file contains a magic comment, it is considered unmodified.
    """
    lines = contents.decode().splitlines()
    # Old style of keeping track of whether a resource file was managed: a comment at the top of the file hasn't been removed.
    if "<!-- Managed automatically by PreTeXt authoring tools -->" in contents.decode():
        log.debug(
            f"Resource file {resource} is managed by PreTeXt using magic comment."
        )
        return True
    # Look in the first two lines for the version number.  This is always in the first or second line if it exists.
    for i in range(min(2, len(lines))):
        if "automatically generated with PreTeXt" in lines[i]:
            # use regex to get version number:
            version = re.search(r"\d+\.\d+\.\d+", lines[i])
            if resource == "requirements.txt" and version:
                return True
            elif version and version[0] in resource_hash_table:
                # Hash file and compare to hash in resource_hash_table
                hash = hashlib.sha256()
                hash.update(contents)
                if hash.hexdigest() == resource_hash_table[version[0]][resource]:
                    log.debug(
                        f"Resource file {resource} is unmodified, compared to hash."
                    )
                    return True
            break
    log.debug(f"Resource file {resource} appears to have been modified.")
    return False


def rs_methods(
    url: str = "", out_path: str = "", format: str = "xml"
) -> t.Optional[str]:
    """
    Attempts to run core methods to get rs services files, and provides backup if no internet connection.
    """
    cache_dir = resources.resource_base_path() / "rs_cache"
    if not cache_dir.exists():
        cache_dir.mkdir()
    # Two cases: format is tgz or xml.  If tgz, then we are trying to download the full tgz file.  If xml, then we are trying to download the xml file.
    if format == "xml":
        assert url != "", "URL must be provided to download xml file."
        assert out_path == "", "Output path must not be provided to download xml file."
        try:
            log.info(f"Downloading rs services file from {url}.")
            services_xml = core.query_runestone_services(url)
            # Write file to cache directory.
            with open(cache_dir / "rs_services.xml", "w") as f:
                f.write(services_xml)
        except Exception as e:
            log.warning(
                f"Could not download rs services file from {url}.  Using cached version instead."
            )
            log.debug(e)
            with open(cache_dir / "rs_services.xml", "r") as f:
                services_xml = f.read()
        finally:
            return services_xml

    elif format == "tgz":
        assert url != "", "URL must be provided to download tgz file."
        assert out_path != "", "Output path must be provided to download tgz file."

        # Split the url into parts to get the filename.
        services_filename = url.split("/")[-1]
        services_cache_path = cache_dir / services_filename
        if not services_cache_path.exists():
            try:
                log.debug(
                    f"Downloading rs services file from {url} to {services_cache_path}."
                )
                core.download_file(url, services_cache_path)
            except Exception as e:
                log.warning(
                    f"Could not download rs services file from {url} and no cached version found."
                )
                raise e
        # get the parent directory of out_path and make sure it exists.
        out_dir = Path(out_path).parent
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        log.debug(f"Extracting rs services file to {out_dir}.")
        # Copy the file to the output path.
        shutil.copyfile(services_cache_path, out_path)

    else:
        log.error(
            f"PTX-BUG: Format {format} not recognized for running ext_rs_methods.  Something is wrong with the pretext script."
        )
    return None
