import os
from collections.abc import Generator
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler
import shutil
from pathlib import Path
import platform
import re
import socketserver
import socket
import subprocess
import logging
import logging.handlers
import psutil
import typing as t
from . import types as pt  # PreTeXt types
from lxml import etree as ET
from lxml.etree import _ElementTree, _Element
from typing import Any, cast, List, Optional


from . import core, templates, constants

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
    current_directory = Path()
    os.chdir(path)
    log.debug(f"Now working in directory {path}")
    try:
        yield
    finally:
        os.chdir(current_directory)
        log.debug(f"Successfully changed directory back to {current_directory}")


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


def project_xml(dirpath: t.Optional[Path] = None) -> _ElementTree:
    if dirpath is None:
        dirpath = Path()  # current directory
    pp = project_path(dirpath)
    if pp is None:
        with templates.resource_path("project.ptx") as project_manifest:
            return ET.parse(project_manifest)
    else:
        project_manifest = pp / "project.ptx"
        return ET.parse(project_manifest)


def requirements_version(dirpath: Optional[Path] = None) -> Optional[str]:
    if dirpath is None:
        dirpath = Path()  # current directory
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
        dirpath = Path()  # current directory
    return ET.tostring(project_xml(dirpath), encoding="unicode")


# TODO: is this ever called?
def target_xml(
    alias: t.Optional[str] = None, dirpath: t.Optional[Path] = None
) -> Optional[_Element]:
    if dirpath is None:
        dirpath = Path()  # current directory
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
        log.error(f"The file {xmlfile} does not exist")
        return False
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
    schemarngfile = core.resources.path("schema", "pretext.rng")

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
    shutil.copytree(core.resources.path("xsl"), output_dir / "core")


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
    # First purge any asset types that are no longer in the clean table:
    dirty_table = {
        asset: dirty_table[asset] for asset in dirty_table if asset in clean_table
    }
    # Then purge ids of assets that no longer exist in the clean table:
    for asset in dirty_table:
        dirty_table[asset] = {
            id: dirty_table[asset][id]
            for id in dirty_table[asset]
            if id in clean_table[asset]
        }
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


def npm_install() -> None:
    with working_directory(core.resources.path("script", "mjsre")):
        log.info("Attempting to install/update required node packages.")
        try:
            subprocess.run("npm install", shell=True)
        except Exception as e:
            log.critical(
                "Unable to install required npm packages.  Please see the documentation."
            )
            log.critical(e)
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


def exit_command(mh: logging.handlers.MemoryHandler) -> None:
    """
    Clean's up at the end of a run.
    Checks to see if anything (errors etc.) is in the memory handler.  If it is, reports that there are errors before the handler gets flushed.  Otherwise, adds a single blank line.
    """
    if len(mh.buffer) > 0:
        print("\n----------------------------------------------------")
        log.info("While running pretext, the following errors occurred:\n")
        mh.flush()
        print("----------------------------------------------------")
        # sys.exit("Exit due to errors.")
    else:
        print("")


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
        return

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
        else:
            log.error("Either add and commit these changes with Git, or run")
            log.error(
                "`pretext deploy -u` to have these changes updated automatically."
            )
            return

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
        directory,
        mesg="Latest build deployed.",
        nojekyll=False,
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


def active_server_port() -> t.Optional[int]:
    """
    Check if a pretext-view server is running already, and if so, return its port number.
    """
    # We look at all currently running processes and check if any are a pretext process that is a child of a pretext process.  This would only happen if we have run a `pretext view` command to start the server, so we can assume that this is the server we are looking for.
    for proc in psutil.process_iter():
        if proc.name() == "pretext" and proc.parent().name() == "pretext":
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
                    and proc.parent().name() == "pretext"
                    and proc.connections()[0].laddr.port == port
                ):
                    log.debug(
                        f"Terminating process with PID {proc.pid} hosting on port {port}"
                    )
                    proc.terminate()
    else:
        # As before, we look for a pretext process that is a child of a pretext process.  This time we terminate that process.
        for proc in psutil.process_iter():
            if proc.name() == "pretext" and proc.parent().name() == "pretext":
                log.debug(f"Terminating process with PID {proc.pid}")
                proc.terminate()
