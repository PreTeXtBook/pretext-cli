import click
import click_logging
import logging
import shutil
import datetime
import os, zipfile, requests, io
import tempfile, shutil
import platform

from . import utils, static, VERSION, CORE_COMMIT
from .static.pretext import pretext as core
from .project import Target, Project


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
@click.version_option(VERSION,message=VERSION)
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
        # create file handler which logs even debug messages
        fh = logging.FileHandler(os.path.join(utils.project_path(),'cli.log'), mode='w')
        fh.setLevel(logging.DEBUG)
        log.addHandler(fh)
        # output info
        log.info(f"PreTeXt project found in `{utils.project_path()}`.")
        os.chdir(utils.project_path())
        if utils.requirements_version() is None:
            log.warning("Project's CLI version could not be detected from `requirements.txt`.")
        elif utils.requirements_version() != VERSION:
            log.warning(f"Using CLI version {VERSION} but project's `requirements.txt`")
            log.warning(f"is configured to use {utils.requirements_version()}. Consider either installing")
            log.warning(f"CLI version {utils.requirements_version()} or updating `requirements.txt` to {VERSION}.")
        else:
            log.debug(f"CLI version {VERSION} matches requirements.txt {utils.requirements_version()}.")
    else:
        log.info("No existing PreTeXt project found.")
    if ctx.invoked_subcommand is None:
        log.info("Run `pretext --help` for help.")
    log.info("")


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
    log.info(f"PreTeXt-CLI version: {VERSION}")
    log.info(f"    PyPI link: https://pypi.org/project/pretextbook/{VERSION}/")
    log.info(f"PreTeXt core resources commit: {CORE_COMMIT}")
    log.info(f"OS: {platform.platform()}")
    log.info(f"Python version: {platform.python_version()}")
    log.info(f"Current working directory: {os.getcwd()}")
    if utils.project_path() is not None:
        log.info(f"PreTeXt project path: {utils.project_path()}")
        log.info("")
        log.info("Contents of project.ptx:")
        log.info("------------------------")
        log.info(utils.project_xml_string())
        log.info("------------------------")
        project = Project()
        project.init_ptxcore()
        for exec_name in project.executables():
            if utils.check_executable(exec_name) is None:
                log.warning(
                    f"Unable to locate the command for <{exec_name}> on your system.")
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
        f.write(f"pretextbook == {VERSION}")
    log.info(f"Success! Open `{directory_fullpath}/source/main.ptx` to edit your document")
    log.info(f"Then try to `pretext build` and `pretext view` from within `{directory_fullpath}`.")


# pretext init
@main.command(short_help="Generates the project manifest for a PreTeXt project in the current directory.", 
    context_settings=CONTEXT_SETTINGS)
@click.option('-f', '--force', is_flag=True, 
              help="Force initialization of project even if project.ptx exists. Duplicate files will be created with timestamps for comparison")
def init(force):
    """
    Generates the project manifest for a PreTeXt project in the current directory. This feature
    is mainly intended for updating existing projects to use this CLI.
    """
    if utils.project_path() is not None and not force:
        log.warning(f"A project already exists in `{utils.project_path()}`.")
        log.warning(f"No project.ptx manifest will be generated.  Use `pretext init -f` to force re-initialization.")
        return
    timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    template_manifest_path = static.path('templates', 'project.ptx')
    project_manifest_path = os.path.abspath("project.ptx")
    if os.path.isfile(project_manifest_path):
        project_manifest_path = os.path.abspath('project-'+timestamp+'.ptx')
        log.warning(
            f"You already have a project.ptx file at, so the one suggested by PreTeXt will been created as {project_manifest_path} for comparison.\n")
    log.info(f"Generating `{project_manifest_path}`.")
    shutil.copyfile(template_manifest_path,project_manifest_path)
    # Create requirements.txt
    requirements_path = os.path.abspath('requirements.txt')
    if os.path.isfile(requirements_path):
        requirements_path = os.path.abspath('requirments-'+timestamp+'.txt')
        log.warning(f"You already have a requirements.txt file; the one suggested by PreTeXt will be created as {requirements_path} for comparison.\n")
    with open(requirements_path,"w") as f:
        f.write(f"pretextbook == {VERSION}")
    # Create publication file if one doesn't exist: 
    template_pub_path = static.path('templates','publication.ptx')
    project_pub_path = os.path.abspath(os.path.join('publication','publication.ptx'))
    if os.path.isfile(project_pub_path):
        project_pub_path = os.path.abspath(os.path.join('publication','publication-'+timestamp+'.ptx'))
        log.warning(
            f"You already have a publication file, so the one suggested by PreTeXt will been created as {project_pub_path} for comparison.\n")
    shutil.copy(template_pub_path, project_pub_path)
    log.info(f"Publication file created at {project_pub_path}.  If you use another publication file, move it or update {project_manifest_path} to point to the location of the file (and delete the new publication file).")
    # Create .gitignore if one doesn't exist
    template_gitignore_path = static.path('templates','.gitignore')
    project_gitignore_path = os.path.abspath(".gitignore")
    if os.path.isfile(project_gitignore_path):
        project_gitignore_path = os.path.abspath(".gitignore-"+timestamp)
        log.warning(f"You already have a .gitignore file, so the one suggested by PreTeXt will be created at {project_gitignore_path} for comparison.\n") 
    shutil.copyfile(template_gitignore_path,project_gitignore_path)
    log.info(f"Created .gitignore file.\n")
    # End by reporting success
    log.info(f"Success! Open {project_manifest_path} to edit your project manifest.")
    log.info(f"Edit your <target/>s to point to your main PreTeXt source file.")


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
@click.option('--clean', is_flag=True, help="Destroy output's target directory before build to clean up previously built files")
@click.option(
    '-g', '--generate', is_flag=True, 
    help='Generate assets in default formats before build')
@click.option(
    '-a', '--assets', default="ALL",
    type=click.Choice(['ALL', 'webwork', 'latex-image', 'sageplot', 'asymptote', 'interactive', 'youtube', 'codelens'], case_sensitive=False), 
    help='If generating, choose to generate ALL or specific assets')
@click.option('-d', '--diagrams', is_flag=True, help='OBSOLETE. Use --generate')
@click.option('-w', '--webwork', is_flag=True, default=False, help='OBSOLETE. Use --generate')
def build(target, format, source, output, stringparam, xsl, publication, clean, generate, assets,
    webwork, diagrams,):
    """
    Process [TARGET] into format specified by project.ptx.
    Also accepts manual command-line options.

    If using certain elements (webwork, latex-image, etc.) then
    using `--generate` may be necessary for a successful build. Generated
    assets are cached so they need not be regenerated in subsequent builds unless
    they are changed.

    Certain builds may require installations not included with the CLI, or internet
    access to external servers. Command-line paths
    to non-Python executables may be set in project.ptx. For more details,
    consult the PreTeXt Guide: https://pretextbook.org/documentation.html
    """
    if diagrams or webwork:
        log.error("Command used an asset option that is now obsolete.")
        log.error("Assets are now generated with `pretext generate` or `pretext build -g`.")
        log.error("Cancelling build. Check `--help` for details.")
        return
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
    if generate and assets=='ALL':
        log.info("Genearting all assets in default formats.")
        project.generate(target_name)
    elif generate:
        log.warning(f"Generating only {assets} assets.")
        project.generate(target_name,asset_list=[assets])
    else:
        log.warning("Assets like latex-images will not be regenerated for this build")
        log.warning("(previously generated assets will be used if they exist).")
    project.build(target_name,clean)

# pretext generate
@main.command(short_help="Generate assets for specified target", 
    context_settings=CONTEXT_SETTINGS)
@click.argument('target', required=False)
@click.option(
    '-a', '--assets', default="ALL",
    type=click.Choice(['ALL', 'webwork', 'latex-image', 'sageplot', 'asymptote', 'interactive', 'youtube'], case_sensitive=False), 
    help='Generate ALL or specific assets')
@click.option('--all-formats', is_flag=True, default=False, 
    help='Generate all possible asset formats rather than the defaults for the given target.')
def generate(target, assets, all_formats):
    """
    Generate assets for the specified target. Asset "generation" is typically
    slower and performed less frequently than "building" a project, but is
    required for many PreTeXt features such as latex-image.

    Certain assets may require installations not included with the CLI, or internet
    access to external servers. Command-line paths
    to non-Python executables may be set in project.ptx. For more details,
    consult the PreTeXt Guide: https://pretextbook.org/documentation.html
    """
    project = Project()
    target_name = target
    if assets == 'ALL':
        log.info("Genearting all assets in default formats.")
        project.generate(target_name)
    else:
        log.info(f"Generating only {assets} assets.")
        project.generate(target_name,asset_list=[generate])


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
@click.option('-g', '--generate', is_flag=True, help="""
    Generate all assets before starting server.
    """)
def view(target,access,port,directory,watch,build,generate):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    TARGET is the name of the <target/> defined in `project.ptx`.
    """
    if directory is not None:
        utils.run_server(directory,access,port)
        return
    target_name=target
    project = Project()
    target = project.target(name=target_name)
    if target is None:
        log.error(f"Target `{target_name}` could not be found.")
        return
    if generate:
        log.info("Generating all assets in default formats.")
        project.generate(target_name)
    if build or watch:
        log.info("Building target.")
        project.build(target_name)
    project.view(target_name,access,port,watch)


# pretext deploy
@main.command(short_help="Deploys Git-managed project to GitHub Pages.",
    context_settings=CONTEXT_SETTINGS)
@click.argument('target', required=False)
@click.option('-u', '--update_source', is_flag=True, required=False)
def deploy(target,update_source):
    """
    Automatically deploys most recent build of [TARGET] to GitHub Pages,
    making it available to the general public.
    Requires that your project is under Git version control
    properly configured with GitHub and GitHub Pages. Deployed
    files will live in `docs` subdirectory of project.
    """
    target_name = target
    project = Project()
    project.deploy(target_name,update_source)

# pretext publish
@main.command(short_help="OBSOLETE: use deploy",
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
    OBSOLETE in favor of `deploy` command. Will be
    removed in a future version.
    """
    log.error("`pretext publish` command is OBSOLETE.")
    log.error("Use `pretext deploy` next time.")
