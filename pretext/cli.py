import click
import click_logging
import logging
import shutil
import os, zipfile, requests, io
import tempfile, shutil
import platform

from . import utils, static
from . import version as cli_version
from .static.pretext import pretext as core
from .project import Target,Project


log = logging.getLogger('ptxlogger')
click_logging.basic_config(log)

def raise_cli_error(message):
    raise click.UsageError(" ".join(message.split()))

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


#  Click command-line interface
@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.pass_context
# Allow a verbosity command:
@click_logging.simple_verbosity_option(
    log,
    help="Sets the severity of log messaging: DEBUG for all, INFO (default) for most, then WARNING, ERROR, and CRITICAL for decreasing verbosity."
)
@click.version_option(cli_version(),message=cli_version())
@click.option('-t', '--targets', is_flag=True, help='Display list of build/view "targets" available in the project manifest.')
def main(ctx,targets):
    """
    Command line tools for quickly creating, authoring, and building PreTeXt projects.

    PreTeXt Guide for authors and publishers:

    - https://pretextbook.org/documentation.html

    PreTeXt CLI README for developers:

    - https://github.com/PreTeXtBook/pretext-cli/

    Use the `--help` option on any CLI command to learn more, for example,
    `pretext build --help`.
    """
    # set verbosity:
    if log.level == 10:
        verbosity = 2
    elif log.level == 50:
        verbosity = 0
    else:
        verbosity = 1
    core.set_verbosity(verbosity)
    if targets:
        Project().print_target_names()
        return
    if utils.project_path() is not None:
        log.info(f"PreTeXt project found in `{utils.project_path()}`.")
        os.chdir(utils.project_path())
    elif ctx.invoked_subcommand is None:
        log.info("No existing PreTeXt project found.")
        log.info("Run `pretext --help` for help.")


# pretext support
@main.command(
    short_help="Use when communicating with PreTeXt support.", 
    context_settings=CONTEXT_SETTINGS)
def support():
    """
    Outputs useful information about your installation needed by
    PreTeXt volunteers when requesting help on the pretext-support
    Google Group.
    """
    log.info("")
    log.info("Please share the following information when posting to the")
    log.info("pretext-support Google Group.")
    log.info("")
    with open(static.path('VERSION'), 'r') as version_file:
        version = version_file.read().strip()
        log.info(f"PreTeXt-CLI version: {version}")
        log.info(f"    PyPI link: https://pypi.org/project/pretextbook/{version}/")
    with open(static.path('CORE_COMMIT'), 'r') as commit_file:
        log.info(f"PreTeXt core resources commit: {commit_file.read().strip()}")
    log.info(f"OS: {platform.platform()}")
    log.info(f"Python version: {platform.python_version()}")
    log.info(f"Current working directory: {os.getcwd()}")
    if utils.project_path() is not None:
        log.info(f"PreTeXt project path: {utils.project_path()}")
        log.info("")
        log.info("Contents of project.ptx:")
        log.info("------------------------")
        log.info(utils.project_xml_string())
    else:
        log.info("No project.ptx found.")


# pretext new
@main.command(short_help="Generates the necessary files for a new PreTeXt project.", 
    context_settings=CONTEXT_SETTINGS)
@click.argument('template', default='book',
              type=click.Choice(['book', 'article', 'hello'], case_sensitive=False))
@click.option('-d', '--directory', type=click.Path(), default='new-pretext-project',
              help="Directory to create/use for the project.")
@click.option('-u', '--url-template', type=click.STRING,
              help="Download a zipped template from its URL.")
def new(template,directory,url_template):
    """
    Generates the necessary files for a new PreTeXt project.
    Supports `pretext new book` (default) and `pretext new article`,
    or generating from URL with `pretext new --url-template [URL]`.
    """
    directory_fullpath = os.path.abspath(directory)
    if utils.project_path(directory_fullpath) is not None:
        log.warning(f"A project already exists in `{utils.project_path(directory_fullpath)}`.")
        log.warning(f"No new project will be generated.")
        return
    log.info(f"Generating new PreTeXt project in `{directory_fullpath}` using `{template}` template.")
    if url_template is not None:
        r = requests.get(url_template)
        archive = zipfile.ZipFile(io.BytesIO(r.content))
    else:
        template_path = static.path('templates', f'{template}.zip')
        archive = zipfile.ZipFile(template_path)
    # find (first) project.ptx to use as root of template
    filenames = [os.path.basename(filepath) for filepath in archive.namelist()]
    project_ptx_index = filenames.index('project.ptx')
    project_ptx_path = archive.namelist()[project_ptx_index]
    project_dir_path = os.path.dirname(project_ptx_path)
    with tempfile.TemporaryDirectory() as tmpdirname:
        for filepath in [filepath for filepath in archive.namelist() if filepath.startswith(project_dir_path)]:
            archive.extract(filepath,path=tmpdirname)
        tmpsubdirname = os.path.join(tmpdirname,project_dir_path)
        shutil.copytree(tmpsubdirname,directory,dirs_exist_ok=True)
    # generate requirements.txt
    with open(os.path.join(directory_fullpath,"requirements.txt"),"w") as f:
        f.write(f"pretextbook == {cli_version()}")
    log.info(f"Success! Open `{directory_fullpath}/source/main.ptx` to edit your document")
    log.info(f"Then try to `pretext build` and `pretext view` from within `{directory_fullpath}`.")


# pretext init
@main.command(short_help="Generates the project manifest for a PreTeXt project in the current directory.", 
    context_settings=CONTEXT_SETTINGS)
def init():
    """
    Generates the project manifest for a PreTeXt project in the current directory. This feature
    is mainly intended for updating existing projects to use this CLI.
    """
    if utils.project_path() is not None:
        log.warning(f"A project already exists in `{utils.project_path()}`.")
        log.warning(f"No project.ptx manifest will be generated.")
        return
    template_manifest_path = static.path('templates', 'project.ptx')
    project_manifest_path = os.path.abspath("project.ptx")
    log.info(f"Generating `{project_manifest_path}`.")
    shutil.copyfile(template_manifest_path,project_manifest_path)
    with open("requirements.txt","w") as f:
        f.write(f"pretextbook == {cli_version()}")
    log.info(f"Success! Open `{project_manifest_path}` to edit your project manifest.")
    log.info(f"Edit your <target/>s to point to your main PreTeXt source file.")
    project_pub_path = os.path.abspath(os.path.join("publication","publication.ptx"))
    if not os.path.isfile(project_pub_path):
        log.warning(f"Note that your publication file should be moved to `{project_pub_path}`, or")
        log.warning(f"`{project_manifest_path}` should be updated to the location of your publication file.")


# pretext build
@main.command(short_help="Build specified target", 
    context_settings=CONTEXT_SETTINGS)
@click.argument('target', required=False)
@click.option('-f', '--format', type=click.Choice(['html','latex','pdf']),
              help='Output format to build.')
@click.option('-i', '--input', 'source', type=click.Path(),
              help='Path to main *.ptx file')
@click.option('-o', '--output', type=click.Path(),
              help='Directory to build files into')
@click.option('-p', '--publication', type=click.Path(), default=None,
              help="Path to publication *.ptx file")
@click.option('-x', '--xsl', type=click.Path(), default=None,
              help="Path to custom xsl file")
@click.option('--stringparam', nargs=2, multiple=True, help="""
              Define a stringparam to use during processing.
              Usage: pretext build --stringparam foo bar --stringparam baz woo
              """)
@click.option('-d', '--diagrams', is_flag=True, help='Regenerate images coded in source (latex-image, etc).')
@click.option('-df', '--diagrams-format', type=click.Choice(['defaults', 'all'], case_sensitive=False), default='defaults', help='Specify whether to build just the "defaults" formats or "all" formats based on output target.')
@click.option('-w', '--webwork', is_flag=True, default=False, help='Reprocess WeBWorK exercises, creating fresh webwork-representations.ptx file')
@click.option('-a', '--only-assets', is_flag=True, default=False, help="Produce requested diagrams (-d) or webwork (-w) but not main build target (useful for large projects that only need to update assets)")
@click.option('--clean', is_flag=True, help="Destroy output's target directory before build to clean up previously built files")
def build(target, format, source, output, stringparam, xsl, publication, webwork, diagrams, diagrams_format, only_assets, clean):
    """
    Process [TARGET] into format specified by project.ptx.
    Also accepts manual command-line options.

    For many formats, images coded in source (latex-image, etc) will only be processed
    when using the --diagrams option.

    If the project included WeBWorK exercises, these must be processed using the
    --webwork option.

    Certain builds may require installations not included with the CLI, or internet
    access to external servers. Command-line paths
    to non-Python executables may be set in project.ptx. For more details,
    consult the PreTeXt Guide: https://pretextbook.org/documentation.html
    """
    target_name = target
    # set up stringparams as dictionary:
    if len(stringparam) > 0:
        stringparams = {p[0] : p[1] for p in stringparam}
    else:
        stringparams = None
    if utils.project_path() is None:
        log.warning(f"No project.ptx manifest was found. Run `pretext init` to generate one.")
        log.warning("Continuing using commandline arguments.")
        if publication is None:
              pass
        target = Target(name=format,format=format,source=source,output_dir=output,
                        publication=publication,stringparams=stringparams)
        project = Project(targets=[target])
    else:
        project = Project()
        if target_name is None:
            log.info(f"Since no build target was supplied, the first target of the "+
                     "project.ptx manifest will be built.")
        target = project.target(name=target_name)
        if target is None:
            log.critical("Build target could not be found in project.ptx manifest.")
            log.critical("Exiting without completing task.")
            return
        #overwrite target with commandline arguments, update project accordingly
        target = Target(xml_element=target.xml_element(),
                        format=format,source=source,output_dir=output,
                        publication=publication,stringparams=stringparams,xsl_path=xsl)
        project = Project(xml_element=project.xml_element(),targets=[target])
    project.build(target_name,webwork,diagrams,diagrams_format,only_assets,clean)


# pretext view
@main.command(short_help="Preview specified target in your browser.", 
    context_settings=CONTEXT_SETTINGS)
@click.argument('target', required=False)
@click.option(
    '-a',
    '--access',
    type=click.Choice(['public', 'private'], case_sensitive=False),
    default='private',
    show_default=True,
    help="""
    Choose whether or not to allow other computers on your local network
    to access your documents using your IP address. (Ignored when used
    in CoCalc, which works automatically.)
    """)
@click.option(
    '-p',
    '--port',
    default=8000,
    show_default=True,
    help="""
    Choose which port to use for the local server.
    """)
@click.option(
    '-d',
    '--directory',
    type=click.Path(),
    help="""
    Serve files from provided directory
    """)
@click.option('-w', '--watch', is_flag=True, help="""
    Run a build before starting server, and then
    watch the status of source files,
    automatically rebuilding target when changes
    are made. Only supports HTML-format targets, and
    only recommended for smaller projects or small
    subsets of projects.
    """)
@click.option('-b', '--build', is_flag=True, help="""
    Run a build before starting server.
    """)
def view(target,access,port,directory,watch,build):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    TARGET is the name of the <target/> defined in `project.ptx`.
    """
    target_name=target
    if directory is not None:
        utils.run_server(directory,access,port)
        return
    else:
        project = Project()
        target = project.target(name=target_name)
    if target is not None:
        project.view(target_name,access,port,watch,build)
    else:
        log.error(f"Target `{target_name}` could not be found.")


# pretext deploy
@main.command(short_help="Deploys Git-managed project to GitHub Pages.",
    context_settings=CONTEXT_SETTINGS)
@click.argument('target', required=False)
@click.option(
    '-m',
    '--commit-message',
    default="Update to PreTeXt project source.",
    show_default=True,
    help="""
    Customize message to leave on Git commit for source updates.
    """)
def deploy(target,commit_message):
    """
    Automatically deploys most recent build of [TARGET] to GitHub Pages,
    making it available to the general public.
    Requires that your project is under Git version control
    properly configured with GitHub and GitHub Pages. Deployed
    files will live in `docs` subdirectory of project.
    """
    target_name = target
    project = Project()
    project.deploy(target_name,commit_message)

# pretext publish
@main.command(short_help="DEPRECATED: use deploy",
    context_settings=CONTEXT_SETTINGS)
@click.argument('target', required=False)
@click.option(
    '-m',
    '--commit-message',
    default="Update to PreTeXt project source.",
    show_default=True,
    help="""
    Customize message to leave on Git commit for source updates.
    """)
@click.pass_context
def publish(ctx,target,commit_message):
    """
    DEPRECATED in favor of `deploy` command. Will be
    removed in a future version.
    """
    log.warning("`pretext publish` command is DEPRECATED and will be removed soon.")
    log.warning("Use `pretext deploy` next time.")
    ctx.forward(deploy)
