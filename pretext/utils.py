import os
import random
import json
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler
import shutil
from pathlib import Path
import platform
import re
import socketserver
import socket
import subprocess
import sys
import logging
import threading
import watchdog.events
import watchdog.observers
import time
import webbrowser
import typing as t
from lxml import etree as ET
from typing import Optional

from . import core, templates

# Get access to logger
log = logging.getLogger("ptxlogger")


@contextmanager
def working_directory(path: Path):
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
def project_path(dirpath: Optional[Path] = None) -> Path:
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


def project_xml(dirpath: t.Optional[Path] = None) -> Path:
    if dirpath is None:
        dirpath = Path()  # current directory
    if project_path(dirpath) is None:
        with templates.resource_path("project.ptx") as project_manifest:
            return ET.parse(project_manifest)
    else:
        project_manifest = project_path(dirpath) / "project.ptx"
        return ET.parse(project_manifest)


def requirements_version(dirpath: Optional[Path] = None) -> str:
    if dirpath is None:
        dirpath = Path()  # current directory
    try:
        with open(project_path(dirpath) / "requirements.txt", "r") as f:
            for line in f.readlines():
                if "pretext" or "pretextbook" in line:
                    return line.split("==")[1].strip()
    except Exception as e:
        log.debug("Could not read `requirements.txt`:")
        log.debug(e)
        return None


def project_xml_string(dirpath: Optional[Path] = None) -> str:
    if dirpath is None:
        dirpath = Path()  # current directory
    return ET.tostring(project_xml(dirpath), encoding="unicode")


def target_xml(
    alias: t.Optional[str] = None, dirpath: t.Optional[Path] = None
) -> ET.Element:
    if dirpath is None:
        dirpath = Path()  # current directory
    if alias is None:
        return project_xml().find("targets/target")  # first target
    xpath = f'targets/target[@name="{alias}"]'
    matches = project_xml().xpath(xpath)
    if len(matches) == 0:
        log.info(
            f"No targets with alias {alias} found in project manifest file project.ptx."
        )
        return None
    return project_xml().xpath(xpath)[0]


# check xml syntax
def xml_syntax_is_valid(xmlfile: Path) -> bool:
    # parse xml
    try:
        source_xml = ET.parse(xmlfile)
        # we need to call xinclude once for each level of nesting (just to check for errors).  25 levels should be more than sufficient
        for i in range(25):
            source_xml.xinclude()
        log.debug("XML syntax appears well formed.")
        if source_xml.getroot().tag != "pretext":
            log.error(
                f'The file {xmlfile} does not have "<pretext>" as its root element.  Did you use a subfile as your source?  Check the project manifest (project.ptx).'
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


def cocalc_project_id() -> t.Optional[str]:
    try:
        with open("/home/user/.smc/info.json") as f:
            return json.load(f)["project_id"]
    except Exception:
        return None


# watchdog handler for watching changes to source
class HTMLRebuildHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, callback):
        self.last_trigger_at = time.time() - 5
        self.callback = callback

    def on_any_event(self, event):
        self.last_trigger_at = time.time()

        # only run callback once triggers halt for a second
        def timeout_callback(handler):
            time.sleep(1.5)
            if time.time() > handler.last_trigger_at + 1:
                handler.last_trigger_at = time.time()
                log.info("\nChanges to source detected.\n")
                handler.callback()

        threading.Thread(target=timeout_callback, args=(self,)).start()


# boilerplate to prevent overzealous caching by preview server, and
# avoid port issues
def binding_for_access(access="private"):
    if access == "private":
        return "localhost"
    else:
        return "0.0.0.0"


def url_for_access(access="private", port=8000):
    if access == "public":
        return f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        return f"http://localhost:{port}"


def serve_forever(
    directory: Path, access="private", port=8000, no_launch: bool = False
):
    log.info(f"Now preparing local server to preview directory `{directory}`.")
    log.info(
        "  (Reminder: use `pretext deploy` to deploy your built project to a public"
    )
    log.info(
        "  GitHub Pages site that can be shared with readers who cannot access your"
    )
    log.info("  personal computer.)")
    log.info("")
    binding = binding_for_access(access)

    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory.as_posix(), **kwargs)

        """HTTP request handler with no caching"""

        def end_headers(self):
            self.send_my_headers()
            SimpleHTTPRequestHandler.end_headers(self)

        def send_my_headers(self):
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
                url = url_for_access(access, port)
                log.info(
                    "Success! The most recent build of your project can be viewed in a web browser at the following url:"
                )
                log.info("    " + url)
                if not no_launch:
                    log.info("This page should open in a new tab automatically.")
                    webbrowser.open(url)
                log.info("Use [Ctrl]+[C] to halt the server.\n")
                httpd.serve_forever()
        except OSError:
            log.warning(f"Port {port} could not be used.")
            port = random.randint(49152, 65535)
            log.warning(f"Trying port {port} instead.\n")


def run_server(
    directory: Path,
    access: str,
    port: int,
    watch_directory: t.Optional[Path] = None,
    watch_callback=lambda: None,
    no_launch: bool = False,
):
    threading.Thread(
        target=lambda: serve_forever(directory, access, port, no_launch), daemon=True
    ).start()
    if watch_directory is not None:
        log.info(f"\nWatching for changes in `{watch_directory}` ...\n")
        event_handler = HTMLRebuildHandler(watch_callback)
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, watch_directory, recursive=True)
        observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\nClosing server...")
        if watch_directory is not None:
            observer.stop()
    if watch_directory is not None:
        observer.join()


# Info on namespaces: http://lxml.de/tutorial.html#namespaces
NSMAP = {
    "xi": "http://www.w3.org/2001/XInclude",
    "xml": "http://www.w3.org/XML/1998/namespace",
}


def nstag(prefix: str, suffix: str) -> str:
    return "{" + NSMAP[prefix] + "}" + suffix


def copy_custom_xsl(xsl_path: Path, output_dir: Path):
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


def check_executable(exec_name: str):
    try:
        exec_cmd = core.get_executable_cmd(exec_name)[0]
        log.debug(f"PTX-CLI: Executable command {exec_name} found at {exec_cmd}")
        return exec_cmd
    except OSError as e:
        log.debug(e)


def check_asset_execs(element, outformats=None):
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
            "Windows": "See https:// pretextbook.org/doc/guide/html/windows-cli-software.html",
            "Darwin": "",
            "Linux": "",
        },
        "pdfeps": {
            "Windows": "See https:// pretextbook.org/doc/guide/html/windows-cli-software.html",
            "Darwin": "",
            "Linux": "",
        },
        "sage": {
            "Windows": "See https://doc.sagemath.org/html/en/installation/index.html#windows",
            "Darwin": "https://doc.sagemath.org/html/en/installation/index.html#macos",
            "Linux": "See https://doc.sagemath.org/html/en/installation/index.html#linux",
        },
        "pageres": {
            "Windows": "See https:// pretextbook.org/doc/guide/html/windows-cli-software.html",
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


def no_project(task: str) -> bool:
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


def show_target_hints(target_format: str, project, task: str):
    """
    This will give the user hints about why they have provided a bad target and make helpful suggestions for them to fix the problem.  We will only run this function when the target_name is not the name in any target in project.ptx.
    """
    # just in case this was called in the wrong place:
    if project.target(name=target_format) is not None:
        return
    # Otherwise continue with hints:
    log.critical(
        f'There is not a target named "{target_format}" for this project.ptx manifest.'
    )
    if target_format in ["html", "pdf", "latex", "epub", "kindle", "braille"]:
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
            f"The available targets to {task} are named: {project.target_names()}.  Try to {task} on of those instead or edit your proejct.ptx manifest."
        )


def npm_install():
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


def playwright_install():
    """
    Run `playwright install` to ensure that its required browsers and tools are available to it.
    """
    try:
        subprocess.run("playwright install", shell=True)
        log.debug("Installed dependencies to capture interactive previews")
    except Exception as e:
        log.critical(
            "Unable to install required playwright packages.  Please see the documentation."
        )
        log.critical(e)
        log.debug("", exc_info=True)


def remove_path(path: Path):
    if path.is_file() or path.is_symlink():
        path.unlink()  # remove the file
    elif path.is_dir():
        shutil.rmtree(path)  # remove dir and all it contains


def exit_command(mh):
    """
    Checks to see if anything (errors etc.) is in the memory handler.  If it is, reports that there are errors before the handler gets flushed.  Otherwise, adds a single blank line.
    """
    if len(mh.buffer) > 0:
        print("\n----------------------------------------------------")
        log.info("While running pretext, the following errors occured:\n")
        mh.flush()
        print("----------------------------------------------------")
        sys.exit(1)
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
