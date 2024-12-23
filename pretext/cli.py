import logging
import logging.handlers
import random
import sys
import time
import click
import click_log
import shutil
import datetime
import os
import zipfile
import requests
import io
import tempfile
import platform
import webbrowser
from pathlib import Path
import subprocess
from pydantic import ValidationError
from typing import Any, Callable, List, Literal, Optional
from functools import update_wrapper


from . import (
    utils,
    resources,
    constants,
    plastex,
    server,
    VERSION,
    CORE_COMMIT,
)


from .project import Project

log = logging.getLogger("ptxlogger")

# click_handler logs all messages to stdout as the CLI runs
click_handler = logging.StreamHandler(sys.stdout)
click_handler.setFormatter(click_log.ColorFormatter())
log.addHandler(click_handler)

# error_flush_handler captures error/critical logs for flushing to stderr at the end of a CLI run
sh = logging.StreamHandler(sys.stderr)
sh.setFormatter(click_log.ColorFormatter())
sh.setLevel(logging.ERROR)
error_flush_handler = logging.handlers.MemoryHandler(
    capacity=1024 * 100,
    flushLevel=100,
    target=sh,
    flushOnClose=False,
)
error_flush_handler.setLevel(logging.ERROR)
log.addHandler(error_flush_handler)


# Add a decorator to provide nice exception handling for validation errors for all commands. It avoids printing a confusing traceback, and also nicely formats validation errors.
def nice_errors(f: Callable[..., None]) -> Any:
    @click.pass_context
    def try_except(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        try:
            return ctx.invoke(f, *args, **kwargs)
        except ValidationError as e:
            log.critical(
                "Failed to parse project.ptx. Check the entire file, including all targets, and fix the following errors:"
            )
            for error in e.errors():
                if error["type"] == "missing":
                    log.error(
                        f"One of the targets has a missing required attribute: {error['loc'][0]}; look for the target with {error['input']}."
                    )
                elif error["type"] == "enum":
                    log.error(
                        f"One of the targets has an attribute with illegal value: @{error['loc'][0]}=\"{error['input']}\" is not allowed.  Pick from the values:{error['msg'].split(': ')[-1].replace('Input should be', '')}."
                    )
                elif error["type"] == "extra_forbidden":
                    log.error(
                        f"Either one of the targets or the root project element has an extra attribute it shouldn't: {error['loc'][0]}=\"{error['input']}\""
                    )
                elif error["type"] == "value_error":
                    log.error(
                        f"In at least one target, you cannot have @{error['loc'][0]}=\"{error['input']}\".  {error['msg'].replace('Value error, ', '')}"
                    )
                else:
                    log.error(f"{error['msg']} ({error['loc']}; {error['type']})")
            log.debug(
                "\n------------------------\nException info:\n------------------------\n",
                exc_info=True,
            )
            return
        except Exception as e:
            log.error(e)
            log.debug("Exception info:\n------------------------\n", exc_info=True)
            return

    return update_wrapper(try_except, f)


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


#  Click command-line interface
@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.pass_context
# Allow a verbosity command:
@click_log.simple_verbosity_option(
    log,
    help="Sets the severity of log messaging: DEBUG for all, INFO (default) for most, then WARNING, ERROR, and CRITICAL for decreasing verbosity.",
)
@click.version_option(VERSION, message=VERSION)
@click.option(
    "-t",
    "--targets",
    is_flag=True,
    help='Display list of build/view "targets" available in the project manifest.',
)
@nice_errors
def main(ctx: click.Context, targets: bool) -> None:
    """
    Command line tools for quickly creating, authoring, and building PreTeXt projects.

    PreTeXt Guide for authors and publishers:

    - https://pretextbook.org/documentation.html

    PreTeXt CLI README for developers:

    - https://github.com/PreTeXtBook/pretext-cli/

    Use the `--help` option on any CLI command to learn more, for example,
    `pretext build --help`.
    """
    if (pp := utils.project_path()) is not None:
        project = Project.parse(pp)
        project.generate_boilerplate()
        if targets:
            for target in project.target_names():
                print(target)
            return
        # create file handler which logs even debug messages
        # TODO: this will likely be moved out of this if to allow manifest-free builds
        logdir = pp / "logs"
        logdir.mkdir(exist_ok=True)
        logfile = logdir / f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        fh = logging.FileHandler(logfile, mode="w")
        fh.setLevel(logging.DEBUG)
        file_log_format = logging.Formatter("{levelname:<8}: {message}", style="{")
        fh.setFormatter(file_log_format)
        log.addHandler(fh)
        # output info
        latest_version = utils.latest_version()
        if latest_version and latest_version != VERSION:
            log.info(
                f"Using PreTeXt-CLI version {VERSION}.  The latest stable version available is {latest_version}. Run `pretext upgrade` to update.\n"
            )
        else:
            log.info(
                f"Using PreTeXt-CLI version: {VERSION}.  This is the latest available version.\n"
            )
        log.info(f"PreTeXt project found in `{utils.project_path()}`.")
        # permanently change working directory for rest of process
        os.chdir(pp)
        if utils.requirements_version() is None:
            log.warning(
                "Project's CLI version could not be detected from `requirements.txt`."
            )
            log.warning("Try `pretext init --refresh` to produce a compatible file.")
        elif utils.requirements_version() != VERSION:
            log.warning(f"Using CLI version {VERSION} but project's `requirements.txt`")
            log.warning(
                f"is configured to use {utils.requirements_version()}. Consider either installing"
            )
            log.warning(
                f"CLI version {utils.requirements_version()} or running `pretext init --refresh`"
            )
            log.warning(f"to update `requirements.txt` to match {VERSION}.")
        else:
            log.debug(
                f"CLI version {VERSION} matches requirements.txt {utils.requirements_version()}."
            )
    else:
        log.info(f"PreTeXt-CLI version: {VERSION}\n")
        utils.ensure_default_project_manifest()
        default_project_path = resources.resource_base_path().parent / "project.ptx"
        project = Project.parse(default_project_path, global_manifest=True)
        log.warning(
            "No project.ptx manifest found in current workspace.  Using global configuration specified in '~/.ptx/project.ptx'."
        )
    # Add project to context so it can be used in subcommands
    ctx.obj = {"project": project}
    if ctx.invoked_subcommand is None:
        log.info("Run `pretext --help` for help.")


@main.result_callback()
def exit(*_, **__):  # type: ignore
    # Exit gracefully:
    utils.exit_command(error_flush_handler)


# pretext support
@main.command(
    short_help="Use when communicating with PreTeXt support.",
    context_settings=CONTEXT_SETTINGS,
)
@nice_errors
def support() -> None:
    """
    Outputs useful information about your installation needed by
    PreTeXt volunteers when requesting help on the pretext-support
    Google Group.
    """
    log.debug("Running pretext support.")
    log.info("")
    log.info("Please share the following information when posting to the")
    log.info("pretext-support Google Group.")
    log.info("")
    log.info(f"PreTeXt-CLI version: {VERSION}")
    log.info(f"    PyPI link: https://pypi.org/project/pretextbook/{VERSION}/")
    log.info(f"PreTeXt core resources commit: {CORE_COMMIT}")
    # Temporarily removing; this is handled by core differently now.
    # log.info(f"Runestone Services version: {core.get_runestone_services_version()}")
    log.info(f"OS: {platform.platform()}")
    log.info(
        f"Python version: {platform.python_version()}, running from {sys.executable}"
    )
    log.info(f"Current working directory: {Path().resolve()}")
    if utils.project_path() is not None:
        log.info(f"PreTeXt project path: {utils.project_path()}")
        log.info("")
        log.info("Contents of project.ptx:")
        log.info("------------------------")
        log.info(utils.project_xml_string())
        log.info("------------------------")

        # Create a project from the project.ptx file
        project = Project.parse()
        project.init_core()

        for exec_name in project.get_executables().model_dump():
            if utils.check_executable(exec_name) is None:
                log.warning(
                    f"Unable to locate the command for <{exec_name}> on your system."
                )
    else:
        log.info("No project.ptx found.")


# pretext upgrade
@main.command(
    short_help="Upgrade PreTeXt-CLI to the latest version using pip.",
    context_settings=CONTEXT_SETTINGS,
)
def upgrade() -> None:
    """
    Upgrade PreTeXt-CLI to the latest version using pip.
    """
    log.info("Upgrading PreTeXt-CLI...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pretext"])
    log.info("Upgrade complete.")


# pretext devscript
@main.command(
    short_help="Alias for the developer pretext/pretext script.",
    context_settings={"help_option_names": [], "ignore_unknown_options": True},
)
@click.argument("args", nargs=-1)
def devscript(args: List[str]) -> None:
    """
    Aliases the core pretext script.
    """
    subprocess.run(
        [
            sys.executable,
            str(resources.resource_base_path() / "core" / "pretext" / "pretext"),
        ]
        + list(args)
    )


# pretext new
@main.command(
    short_help="Generates all the necessary files for a new PreTeXt project.",
    context_settings=CONTEXT_SETTINGS,
)
@click.argument(
    "template",
    default="book",
    type=click.Choice(constants.NEW_TEMPLATES, case_sensitive=False),
)
@click.option(
    "-d",
    "--directory",
    type=click.Path(),
    default="new-pretext-project",
    help="Directory to create/use for the project.",
)
@click.option(
    "-u",
    "--url-template",
    type=click.STRING,
    help="Download a zipped template from its URL.",
)
@nice_errors
def new(template: str, directory: Path, url_template: str) -> None:
    """
    Generates all the necessary files for a new PreTeXt project.
    Supports `pretext new book` (default) and `pretext new article`,
    or generating from URL with `pretext new --url-template [URL]`.
    """
    directory_fullpath = Path(directory).resolve()
    if utils.project_path(directory_fullpath) is not None:
        log.error(
            f"A project already exists in `{utils.project_path(directory_fullpath)}`."
        )
        log.error("No new project will be generated.")
        return
    log.info(f"Generating new PreTeXt project in `{directory_fullpath}`")
    directory_fullpath.mkdir(exist_ok=True)
    if url_template is not None:
        log.info(f"Using template at `{url_template}`")
        # get project and extract to directory
        r = requests.get(url_template)
        archive = zipfile.ZipFile(io.BytesIO(r.content))
        with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:
            archive.extractall(tmpdirname)
            content_path = [Path(tmpdirname) / i for i in os.listdir(tmpdirname)][0]
            shutil.copytree(content_path, directory_fullpath, dirs_exist_ok=True)
    else:
        log.info(f"Using `{template}` template.")
        # copy project from installed resources
        template_path = resources.resource_base_path() / "templates" / f"{template}"
        shutil.copytree(template_path, directory_fullpath, dirs_exist_ok=True)
        # generate missing boilerplate
        with utils.working_directory(directory_fullpath):
            project_path = utils.project_path()
            if project_path is None:
                project = Project()
            else:
                project = Project.parse(project_path)
            project.generate_boilerplate(update_requirements=True)


# pretext init
@main.command(
    short_help="Generates/updates CLI-specific files for the current version of PreTeXt-CLI.",
    context_settings=CONTEXT_SETTINGS,
)
@click.option(
    "-r",
    "--refresh",
    is_flag=True,
    help="Refresh initialization of project even if project.ptx exists.",
)
@click.option(
    "-f",
    "--file",
    "files",
    help="Specify file to refresh.",
    multiple=True,
    type=click.Choice([r for r in constants.PROJECT_RESOURCES], case_sensitive=False),
)
@nice_errors
def init(refresh: bool, files: List[str]) -> None:
    """
    Generates/updates CLI-specific files for the current version of PreTeXt-CLI.
    This feature is mainly intended for updating existing PreTeXt projects to use this CLI,
    or to update project files generated from earlier CLI versions.

    If --refresh is used, files will be generated even if the project has already been initialized.
    Existing files won't be overwritten; a copy of the fresh initialized file will be created
    with a timestamp in its filename for comparison.
    """
    project_path = utils.project_path()
    if project_path is None:
        project = Project()
    else:
        if refresh or len(files) > 0:
            project = Project.parse(project_path)
        else:
            log.warning(f"A project already exists in `{project_path}`.")
            log.warning(
                "Use `pretext init --refresh` to refresh initialization of an existing project"
            )
            log.warning("or `pretext init --file FILENAME` to refresh a specific file.")
            return

    project.generate_boilerplate(
        skip_unmanaged=False, update_requirements=True, resources=files
    )

    if project_path is None:
        log.info("Success! Open project.ptx to edit your project manifest.")
        log.info(
            "Edit your <target/>s to point to the location of your PreTeXt source files."
        )
    else:
        log.info(
            "Success! Your project files have been refreshed. If you manage any of these"
        )
        log.info(
            "manually, be sure to compare these new versions with your old .bak files."
        )


# pretext build
@main.command(short_help="Build specified target", context_settings=CONTEXT_SETTINGS)
@click.argument("target_name", required=False, metavar="target")
@click.option(
    "--clean",
    is_flag=True,
    help="Destroy output's target directory before build to clean up previously built files",
)
@click.option(
    "-g",
    "--generate",
    is_flag=True,
    help="Force (re)generates assets for targets, even if they haven't changed since they were last generated.  (Use `pretext generate` for more fine-grained control of manual asset generation.)",
)
@click.option(
    "-q",
    "--no-generate",
    is_flag=True,
    help="Do not generate assets for target, even if their source has changed since the last time they were generated.",
)
@click.option(
    "-t",
    "--theme",
    is_flag=True,
    help="Only build the theme for the target, without performing any other build or generate steps.  (Themes are automatically built when building a target.)",
)
@click.option(
    "-x",
    "--xmlid",
    type=click.STRING,
    help="xml:id of the root of the subtree to be built.",
)
@click.option(
    "--no-knowls",
    is_flag=True,
    help="Use hyperlinks instead of knowls (e.g. for previewing individual sections when knowl files from other sections may not exist)",
)
@click.option(
    "--deploys",
    is_flag=True,
    help="Build all targets configured to be deployed.",
)
@click.option(
    "-i",
    "--input",
    "source_file",
    type=click.Path(),
    help="Override the source file from the manifest by providing a path to the input.",
)
@click.pass_context
@nice_errors
def build(
    ctx: click.Context,
    target_name: Optional[str],
    clean: bool,
    generate: bool,
    no_generate: bool,
    theme: bool,
    xmlid: Optional[str],
    no_knowls: bool,
    deploys: bool,
    source_file: Optional[str],
) -> None:
    """
    Build [TARGET], which can be the name of a target specified by project.ptx or the name of a pretext file.

    If using elements that require separate generation of assets (e.g., webwork, latex-image, etc.) then these will be generated automatically if their source has changed since the last build.  You can suppress this with the `--no-generate` flag, or force a regeneration with the `--generate` flag.

    Certain builds may require installations not included with the CLI, or internet
    access to external servers. Command-line paths
    to non-Python executables may be set in project.ptx. For more details,
    consult the PreTeXt Guide: https://pretextbook.org/documentation.html
    """

    # Set up project and target based on command line arguments and project.ptx

    # Supply help if not in project subfolder
    # NOTE: we no longer need the following since we have added support for building without a manifest.
    # if utils.cannot_find_project(task="build"):
    #    return
    # Create a new project, apply overlay, and get target. Note, the CLI always finds changes to the root folder of the project, so we don't need to specify a path to the project.ptx file.
    # Use the project discovered in the main command.
    project = ctx.obj["project"]

    # Check to see whether target_name is a path to a file:
    if target_name and Path(target_name).is_file():
        log.debug(
            f"target is a source file {Path(target_name).resolve()}.  Using this to override input."
        )
        log.warning(
            "Building standalone documents is an experimental feature and the interface may change."
        )
        # set the source_file to that target_name and reset target_name to None
        source_file = target_name
        target_name = None

    # Now create the target if the target_name is not missing.
    try:
        # deploys flag asks to build multiple targets: all that have deploy set.
        if deploys and len(project.deploy_targets()) > 0:
            targets = project.deploy_targets()
        elif target_name is None and source_file is not None:
            # We are in the case where we are building a standalone document, so we build a default target if there are no standalone targets or find the first target with standalone="yes".
            if len(project.standalone_targets()) > 0:
                targets = [project.standalone_targets()[0]]
            else:
                target = project.new_target(
                    name="standalone",
                    format="pdf",
                    standalone="yes",
                    output_dir=Path(source_file).resolve().parent,
                )
                targets = [target]
                log.debug(f"Building standalone document with target {target.name}")
                log.debug(target)
        else:
            targets = [project.get_target(name=target_name)]
    except AssertionError as e:
        log.warning("Assertion error in getting target.")
        utils.show_target_hints(target_name, project, task="build")
        log.critical("Exiting without completing build.")
        log.debug(e, exc_info=True)
        return

    # If theme flag is set, only build the theme
    if theme:
        try:
            for t in targets:
                t.build_theme()
        except Exception as e:
            log.error(f"Failed to build theme: {e}")
            log.debug("Exception info:\n------------------------\n", exc_info=True)
        finally:
            # Theme flag means to only build the theme, so we...
            return

    # If input/source_file is given, override the source file for the target
    if source_file is not None:
        for t in targets:
            t.source = Path(source_file).resolve()
            log.warning(f"Overriding source file for target with: {t.source}")
            log.debug(t)

    # Call generate if flag is set
    if generate and not no_generate:
        try:
            for t in targets:
                log.info(f"Generating assets for {t.name}")
                t.generate_assets(only_changed=False, xmlid=xmlid)
            no_generate = True
        except Exception as e:
            log.error(f"Failed to generate assets: {e} \n")
            log.debug("Debug Info:\n", exc_info=True)
    elif generate and no_generate:
        log.warning(
            "Using the `-g/--generate` flag together with `-q/--no-generate` doesn't make sense.  Proceeding as if neither flag was set."
        )
        generate = False
        no_generate = False

    # Call build
    try:
        for t in targets:
            log.info(f"Building target {t.name}")
            if xmlid is not None:
                log.info(f"with root of tree below {xmlid}")
            t.build(
                clean=clean, generate=not no_generate, xmlid=xmlid, no_knowls=no_knowls
            )
        log.info("\nSuccess! Run `pretext view` to see the results.\n")
    except ValidationError as e:
        # A validation error at this point must be because the publication file is invalid, which only happens if the /source/directories/@generated|@external attributes are missing.
        log.critical(
            "It appears there is an error with your publication file.  Are you missing the required source/directories/@external and @generated attributes?"
        )
        log.critical("Failed to build.  Exiting...")
        log.debug(e)
        log.debug(
            "\n------------------------\nException info:\n------------------------\n",
            exc_info=True,
        )
        return
    except Exception as e:
        log.critical(e)
        log.debug("Exception info:\n------------------------\n", exc_info=True)
        log.info("------------------------")
        log.critical("Failed to build.  Exiting...")
        return


# pretext generate
@main.command(
    short_help="Generate specified assets for default target or targets specified by `-t`",
    context_settings=CONTEXT_SETTINGS,
)
@click.argument(
    "assets", type=click.Choice(constants.ASSETS, case_sensitive=False), nargs=-1
)
@click.option(
    "-t",
    "--target",
    "target_name",
    type=click.STRING,
    help="Name of target to generate assets for (if not specified, first target from manifest is used).",
)
@click.option(
    "-x", "--xmlid", type=click.STRING, help="xml:id of element to be generated."
)
@click.option(
    "-q",
    "--only-changed",
    is_flag=True,
    default=False,
    help="Limit generation of assets to only those that have changed since last call to pretext.",
)
@click.option(
    "--all-formats",
    is_flag=True,
    default=False,
    help="Generate all possible asset formats rather than just the defaults for the specified target.",
)
@click.option(
    "--non-pymupdf",
    is_flag=True,
    default=False,
    help="Used to revert to non-pymupdf (legacy) method for generating svg and png.",
)
@click.pass_context
@nice_errors
def generate(
    ctx: click.Context,
    assets: List[str],
    target_name: Optional[str],
    all_formats: bool,
    only_changed: bool,
    xmlid: Optional[str],
    non_pymupdf: bool,
) -> None:
    """
    Generate specified (or all) assets for the default target (first target in "project.ptx"). Asset "generation" is typically
    slower and performed less frequently than "building" a project, but is
    required for many PreTeXt features such as webwork and latex-image.

    Certain assets may require installations not included with the CLI, or internet
    access to external servers. Command-line paths
    to non-Python executables may be set in project.ptx. For more details,
    consult the PreTeXt Guide: https://pretextbook.org/documentation.html
    """

    # If no assets are given as arguments, then assume 'ALL'
    if assets == ():
        assets = ["ALL"]

    if utils.cannot_find_project(task="generate assets for"):
        return

    project = ctx.obj["project"]
    # Now create the target if the target_name is not missing.
    try:
        target = project.get_target(name=target_name)
    except AssertionError as e:
        utils.show_target_hints(target_name, project, task="generating assets for")
        log.critical("Exiting without completing build.")
        log.debug(e, exc_info=True)
        return

    try:
        log.debug(f'Generating assets in for the target "{target.name}".')
        target.generate_assets(
            requested_asset_types=assets,
            all_formats=all_formats,
            only_changed=only_changed,  # Unless requested, generate all assets, so don't check the cache.
            xmlid=xmlid,
            non_pymupdf=non_pymupdf,
        )
        log.info("Finished generating assets.\n")
    except ValidationError as e:
        # A validation error at this point must be because the publication file is invalid, which only happens if the /source/directories/@generated|@external attributes are missing.
        log.critical(
            "It appears there is an error with your publication file.  Are you missing the required source/directories/@external and @generated attributes?"
        )
        log.critical("Failed to build.  Exiting...")
        log.debug(e)
        log.debug(
            "\n------------------------\nException info:\n------------------------\n",
            exc_info=True,
        )
        return
    except Exception as e:
        log.critical(e)
        log.debug("Exception info:\n------------------------\n", exc_info=True)
        log.info("------------------------")
        log.critical("Generating assets as failed.  Exiting...")
        return


# pretext view
@main.command(
    short_help="Preview specified target based on its format.",
    context_settings=CONTEXT_SETTINGS,
)
@click.argument("target_name", metavar="target", required=False)
@click.option(
    "-a",
    "--access",
    type=click.Choice(["public", "private"], case_sensitive=False),
    default="private",
    show_default=True,
    help="""
    If running a local server,
    choose whether or not to allow other computers on your local network
    to access your documents using your IP address.
    """,
)
@click.option(
    "-p",
    "--port",
    type=click.INT,
    default=8128,
    help="""
    If running a local server,
    choose which port to use.
    (Ignored when used
    in CoCalc, which works automatically.)
    """,
)
@click.option(
    "-b",
    "--build",
    is_flag=True,
    help="""
    Run a build before viewing.
    """,
)
@click.option(
    "-g",
    "--generate",
    is_flag=True,
    help="Generate all assets before viewing",
)
@click.option(
    "--no-launch",
    is_flag=True,
    help="By default, pretext view tries to launch the default application to view the specified target.  Setting this suppresses this behavior.",
)
@click.option(
    "-r",
    "--restart-server",
    is_flag=True,
    default=False,
    help="Force restart the local http server in case it is already running.",
)
@click.option(
    "-s",
    "--stop-server",
    is_flag=True,
    default=False,
    help="Stop the local http server if running.",
)
@click.option(
    "-d",
    "--stage",
    is_flag=True,
    default=False,
    help="View the staged deployment.",
)
@click.option(
    "--default-server",
    is_flag=True,
    default=False,
    help="Use the standard python server, even if in a codespace (for debugging)",
)
@click.pass_context
@nice_errors
def view(
    ctx: click.Context,
    target_name: str,
    access: Literal["public", "private"],
    port: int,
    build: bool,
    generate: bool,
    no_launch: bool,
    restart_server: bool,
    stop_server: bool,
    stage: bool,
    default_server: str,
) -> None:
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    TARGET is the name of a <target/> defined in `project.ptx` (defaults to the first target).

    After running this command, you can switch to a new terminal to rebuild your project and see the changes automatically reflected in your browser.

    If a server is already running, no new server will be started (nor will it need to be), unless you pass the `--restart-server` flag. You can stop a running server with CTRL+C or by passing the `--stop-server` flag.
    """

    # pretext view -s should immediately stop the server and do nothing else.
    if utils.cannot_find_project(task="view the output for"):
        return
    project = Project.parse()

    if stop_server:
        try:
            project_hash = utils.hash_path(project.abspath())
            current_server = server.active_server_for_path_hash(project_hash)
            log.info("\nStopping server.")
            if current_server:
                current_server.terminate()
        except Exception as e:
            log.warning("Failed to stop server.")
            log.debug(e, exc_info=True)
        finally:
            return

    try:
        target = project.get_target(name=target_name, log_info_for_none=not stage)
    except AssertionError as e:
        utils.show_target_hints(target_name, project, task="view")
        log.critical("Exiting.")
        log.debug(e, exc_info=True)
        return

    # Call generate if flag is set
    if generate:
        try:
            target.generate_assets(only_changed=False)
        except Exception as e:
            log.warning(f"Failed to generate assets: {e}")
            log.debug("", exc_info=True)
    # Call build if flag is set
    if build:
        try:
            target.build()
        except Exception as e:
            log.warning(f"Failed to build: {e}")
            log.debug("Exception info:\n------------------------\n", exc_info=True)

    # Set up the url path and target name
    if stage:
        target_name = "staged deployment"
        url_path = "/" + project.stage.as_posix()
    else:
        target_name = f"target `{target.name}`"
        url_path = "/" + target.output_dir_relpath().as_posix()

    in_codespace = os.environ.get("CODESPACES")

    if in_codespace and not default_server:
        log.info(
            "Running in a codespace, so using the codespace server instead of the standard python server."
        )
        if port == 8128:
            port = random.randint(8129, 8999)
        # set the url
        url_base = utils.url_for_access(access=access, port=port)
        url = url_base + url_path
        log.info(f"Server will soon be available at {url_base}")
        utils.start_codespace_server(port=port, access=access)
        if no_launch:
            log.info(f"The {target_name} will be available at {url}")
        else:
            seconds = 2
            log.info(f"Opening browser for {target_name} at {url} in {seconds} seconds")
            time.sleep(seconds)
            webbrowser.open(url)
        return
    # Start server if there isn't one running already:
    project_hash = utils.hash_path(project.abspath())
    current_server = server.active_server_for_path_hash(project_hash)
    if restart_server and current_server is not None:
        log.info(
            f"Terminating existing server {current_server.pid} on port {current_server.port}"
        )
        current_server.terminate()
        current_server = None
    # Double check that the current server really is active:
    if current_server is not None and current_server.is_active_server():
        url_base = utils.url_for_access(access=access, port=current_server.port)
        url = url_base + url_path
        log.info(f"Server is already available at {url_base}")
        if no_launch:
            log.info(f"The {target_name} is available at {url}")
        else:
            log.info(f"Now opening browser for {target_name} at {url}")
            webbrowser.open(url)
    # otherwise, start a server
    else:
        log.info(
            f"Now preparing local server to preview your project directory `{project.abspath()}`."
        )
        log.info(
            "  (Reminder: use `pretext deploy` to deploy your built project to a public"
        )
        log.info(
            "  GitHub Pages site that can be shared with readers who cannot access your"
        )
        log.info("  personal computer.)")
        log.info("")

        def callback(actual_port: int) -> None:
            url_base = utils.url_for_access(access=access, port=actual_port)
            url = url_base + url_path
            log.info(f"Server will soon be available at {url_base}")
            if no_launch:
                log.info(f"The {target_name} will be available at {url}")
            else:
                log.info(f"Opening browser for {target_name} at {url}")
                webbrowser.open(url)

        log.info("starting server ...")
        server.start_server(project.abspath(), access, port, callback)


# pretext deploy
@main.command(
    short_help="Deploys Git-managed project to GitHub Pages.",
    context_settings=CONTEXT_SETTINGS,
)
@nice_errors
@click.pass_context
@click.option("-u", "--update-source", is_flag=True, required=False)
@click.option("-s", "--stage-only", is_flag=True, required=False)
@click.option("-p", "--preview", is_flag=True, required=False)
def deploy(
    ctx: click.Context, update_source: bool, stage_only: bool, preview: bool
) -> None:
    """
    Automatically deploys project to GitHub Pages,
    making it available to the general public.
    Requires that your project is under Git version control
    properly configured with GitHub and GitHub Pages. Deployed
    files will live in the gh-pages branch of your repository.
    """
    if utils.cannot_find_project(task="deploy"):
        return
    project = ctx.obj["project"]
    project.stage_deployment()
    if stage_only:
        return
    if preview:
        ctx.invoke(view, stage=True)
    else:
        project.deploy(update_source=update_source, skip_staging=True)


# pretext import
@main.command(
    short_help="Experimental: convert a latex file to pretext",
    context_settings=CONTEXT_SETTINGS,
    name="import",
)
@nice_errors
@click.pass_context
@click.argument("latex_file", required=True)
@click.option("-o", "--output", help="Specify output directory", required=False)
def import_command(ctx: click.Context, latex_file: str, output: str) -> None:
    """
    Experimental: convert a latex file to pretext
    """
    latex_file_path = Path(latex_file).resolve()
    if not latex_file_path.exists():
        log.error(f"File {latex_file_path} does not exist.")
        return
    if output is not None:
        output_path = Path(output).resolve()
        if not output_path.exists():
            log.warning("Output directory does not exist. Creating it.")
            output_path.mkdir(parents=True)
    else:
        output_path = Path.cwd() / "imports" / latex_file_path.stem
        output_path.mkdir(parents=True, exist_ok=True)
    # Now we use plastex to convert:
    log.info(f"Converting {latex_file_path} to PreTeXt.")
    with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:
        temp_path = Path(tmpdirname) / "import"
        temp_path.mkdir()
        log.info(f"Using temporary directory {temp_path}")
        # change to this directory to run plastex
        with utils.working_directory(temp_path):
            try:
                plastex.convert(latex_file_path, output_path)
                shutil.copytree(temp_path, output_path, dirs_exist_ok=True)
                log.debug(f"Conversion done in {temp_path}")
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n------------------------\n", exc_info=True)
                return
