import click
import click_logging
import json
from lxml import etree as ET
import logging
import os
import sys
import shutil
import socket
import subprocess
import os, zipfile, requests, io
import tempfile, shutil
from . import utils, static
from . import version as cli_version
from . import build as builder
from .static.pretext import pretext as core


log = logging.getLogger('ptxlogger')
click_logging.basic_config(log)

def raise_cli_error(message):
    raise click.UsageError(" ".join(message.split()))


#  Click command-line interface
@click.group()
# Allow a verbosity command:
@click_logging.simple_verbosity_option(log, help="Sets the severity of warnings: DEBUG for all; CRITICAL for almost none.  ERROR, WARNING, or INFO (default) are also options.")
@click.version_option(cli_version(),message=cli_version())
def main():
    """
    Command line tools for quickly creating, authoring, and building
    PreTeXt documents.
    """
    # set verbosity:
    if log.level == 10:
        verbosity = 2
    elif log.level == 50:
        verbosity = 0
    else:
        verbosity = 1
    core.set_verbosity(verbosity)
    if utils.project_path() is not None:
        log.info(f"PreTeXt project found in `{utils.project_path()}`.")
        os.chdir(utils.project_path())


# pretext new
@main.command(short_help="Generates the necessary files for a new PreTeXt project.")
@click.argument('template', default='book',
              type=click.Choice(['book', 'article'], case_sensitive=False))
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
    static_dir = os.path.dirname(static.__file__)
    if url_template is not None:
        r = requests.get(url_template)
        archive = zipfile.ZipFile(io.BytesIO(r.content))
    else:
        template_path = os.path.join(static_dir, 'templates', f'{template}.zip')
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
    log.info(f"Success! Open `{directory_fullpath}/source/main.ptx` to edit your document")
    log.info(f"Then try to `pretext build` and `pretext view` from within `{directory_fullpath}`.")

# pretext init
@main.command(short_help="Generates the project manifest for a PreTeXt project in the current directory.")
def init():
    """
    Generates the project manifest for a PreTeXt project in the current directory. This feature
    is mainly intended for updating existing projects to use this CLI.
    """
    directory_fullpath = os.path.abspath('.')
    if utils.project_path(directory_fullpath) is not None:
        log.warning(f"A project already exists in `{utils.project_path(directory_fullpath)}`.")
        log.warning(f"No project manifest will be generated.")
        return
    log.info(f"Generating new PreTeXt manifest in `{directory_fullpath}`.")
    static_dir = os.path.dirname(static.__file__)
    manifest_path = os.path.join(static_dir, 'templates', 'project.ptx')
    project_ptx_path = os.path.join(directory_fullpath,"project.ptx")
    shutil.copyfile(manifest_path,project_ptx_path)
    log.info(f"Success! Open `{project_ptx_path}` to edit your manifest.")
    log.info(f"Edit your <target/>s to point to your PreTeXt source and publication files.")

# pretext build
@main.command(short_help="Build specified target")
@click.argument('target', required=False)
@click.option('-i', '--input', 'source', type=click.Path(), show_default=True,
              help='Path to main *.ptx file')
@click.option('-o', '--output', type=click.Path(), default=None, show_default=True,
              help='Path to main output directory')
@click.option('-p', '--publisher', type=click.Path(), default=None, help="Publisher file name, with path relative to base folder")
@click.option('--param', multiple=True, help="""
              Define a stringparam to use during processing. Usage: pretext build --param foo:bar --param baz:woo
""")
@click.option('-d', '--diagrams', is_flag=True, help='Regenerate images coded in source (latex-image, etc) using pretext script')
@click.option('-df', '--diagrams-format', default='svg', type=click.Choice(['svg', 'pdf', 'eps', 'tex'], case_sensitive=False), help="Specify output format for generated images (svg, png, etc).") # Add back in 'png' and 'all' when png works on Windows.
@click.option('-w', '--webwork', is_flag=True, default=False, help='Reprocess WeBWorK exercises, creating fresh webwork-representations.ptx file')
@click.option('-oa', '--only-assets', is_flag=True, default=False, help="Produce requested diagrams (-d) or webwork (-w) but not main build target (useful for large projects that only need to update assets")
@click.option('--pdf', is_flag=True, help='Compile LaTeX output to PDF using commandline pdflatex')
def build(target, source, output, param, publisher, webwork, diagrams, diagrams_format, only_assets, pdf):
    """
    Process PreTeXt files into specified format.

    For html, images coded in source (latex-image, etc) are only processed using the --diagrams option.

    If the project included WeBWorK exercises, these must be processed using the --webwork option.
    """
    # locate manifest:
    manifest_dir = utils.project_path()
    if manifest_dir is None:
        log.warning(f"No project manifest was found.  Run `pretext init` to generate one.")
        manifest = None
        # if no target has been specified, set to old default of html.  Then set any other defaults
        if target is None:
            target = 'html'
        if source is None:
            source = 'source/main.ptx'
        if output is None:
            output = f'output/{target}'
        # set target_format to target ragardless:
        if target != 'html' and target != 'latex':
            log.critical(f'Without a project manifest, you can only build "html" or "latex".  Exiting...')
            sys.exit(f"`pretext build` did not complete.  Please try again.")
        target_format = target
    else:
        manifest = 'project.ptx'
            
    # Now check if no target was provided, in which case, set to first target of manifest
    if target is None:
        target = utils.update_from_project_xml(target, 'targets/target/@name')
        log.info(f"Since no build target was supplied, we will build {target}, the first target of the project manifest {manifest} in {manifest_dir}")
    
    #if the project manifest doesn't have the target alias, exit build
    if utils.target_xml(alias=target) is None:
        log.critical("Build target does not exist in project manifest project.ptx")
        sys.exit("Exiting without completing task.")

    # Pull build info (source/output/params/etc) when not already supplied by user:
    print(f"source = {source}, output = {output}, publisher = {publisher}")
    if source is None:
        source = utils.target_xml(alias=target).find('source').text.strip()
        log.debug(f"No source provided, using {source}, taken from manifest")
    if output is None:
        output = utils.target_xml(alias=target).find('output-dir').text.strip()
        log.debug(f"No output provided, using {output}, taken from manifest")
    if publisher is None:
        try:
            publisher = utils.target_xml(alias=target).find('publication').text.strip()
            log.debug(f"No publisher file provided, using {publisher}, taken from manifest")
        except:
            log.warning(f"No publisher file was found in {manifest}, will try to build anyway.")
            pass
    # TODO: get params working from manifest.

    # Set target_format to the correct thing
    try: 
        target_format = utils.target_xml(alias=target).find('format').text.strip()
        log.debug(
            f"Setting the target format to {target_format}, taken from manifest for target {target}")
    except:
        target_format = target
        log.warning(f"No format listed in the manifest for the target {target}.  Will try to build using {target} as the format.")

    # Check for xml syntax errors and quit if xml invalid:
    utils.xml_syntax_check(source)
    # Validate xml against schema; continue with warning if invalid:
    utils.schema_validate(source)
    # set up stringparams as dictionary:
    # TODO: exit gracefully if string params were not entered in correct format.
    param_list = [p.split(":") for p in param]
    stringparams = {p[0].strip(): ":".join(p[1:]).strip() for p in param_list}
    if publisher:
        stringparams['publisher'] = publisher
    if 'publisher' in stringparams:
        stringparams['publisher'] = os.path.abspath(stringparams['publisher'])
        if not(os.path.isfile(stringparams['publisher'])):
            log.error(f"You or the manifest supplied {stringparams['publisher']} as a publisher file, but it doesn't exist at that location.  Will try to build anyway.")
            # raise ValueError('Publisher file ({}) does not exist'.format(stringparams['publisher']))
        stringparams['publisher'] = stringparams['publisher'].replace(os.sep, '/')

    # set up source (input) and output as absolute paths
    source = os.path.abspath(source)
    output = os.path.abspath(output)
    # put webwork-representations.ptx in same dir as source main file
    webwork_output = os.path.dirname(source)
    #build targets:
    if webwork:
        # prepare params; for now assume only server is passed
        # see documentation of pretext core webwork_to_xml
        # handle this exactly as in webwork_to_xml (should this
        # be exported in the pretext core module?)
        try:
            server_params = (stringparams['server'])
        except Exception as e:
            root_cause = str(e)
            log.warning("No server name, {}.  Using default https://webwork-ptx.aimath.org".format(root_cause))
            server_params = "https://webwork-ptx.aimath.org"
        builder.webwork(source, webwork_output, stringparams, server_params)
    if diagrams:
        builder.diagrams(source,'generated_assets',stringparams,diagrams_format)
    else:
        source_xml = ET.parse(source)
        source_xml.xinclude()
        if source_xml.find("//latex-image") is not None or source_xml.find("//sageplot") is not None:
            log.warning("There are <latex-image/> or <sageplot/> in source, but these will not be (re)built. Run pretext build with the `-d` flag if updates are needed.")
    if target_format=='html' and not only_assets:
        builder.html(source,output,stringparams)
    if target_format=='latex' and not only_assets:
        builder.latex(source,output,stringparams)
        if pdf:
            with utils.working_directory(output):
                subprocess.run(['pdflatex','main.tex'])

# pretext view
@main.command(short_help="Preview built PreTeXt documents in your browser.")
@click.option('-t', '--target', default=None)
@click.option(
    '-a',
    '--access',
    type=click.Choice(['public', 'private', 'cocalc'], case_sensitive=False),
    default='private',
    show_default=True,
    help="""
    Choose whether or not to allow other computers on your local network
    to access your documents using your IP address, with special option
    to support CoCalc.com users.
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
    '-c',
    '--custom',
    is_flag=True,
    help="""
    Override defaults with those set in project.ptx.
    """)
def view(target,access,port,custom):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    """
    if custom:
        access = utils.update_from_project_xml(access,'view/access')
        port = int(utils.update_from_project_xml(port,'view/port'))

    target_path = utils.target_xml(alias=target).find('output-dir').text.strip()

    directory = os.path.abspath(target_path)
    if not utils.directory_exists(directory):
        raise_cli_error(f"""
        The directory `{directory}` does not exist.
        Maybe try `pretext build` first?
        """)
    if access=='cocalc':
        binding = "0.0.0.0"
        project_id = json.loads(open('/home/user/.smc/info.json').read())['project_id']
        url = f"https://cocalc.com/{project_id}/server/{port}/"
    elif access=='public':
        binding = "0.0.0.0"
        url = f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        binding = "localhost"
        url = f"http://{binding}:{port}"
    utils.run_server(directory,binding,port,url)

# pretext publish
@main.command(short_help="Prepares project for publishing on GitHub Pages.")
def publish():
    """
    Prepares the project locally for HTML publication on GitHub Pages to make
    the built document available to the general public.
    Only supports the default `output/html` build directory.
    Requires Git and a GitHub account.
    """
    if not utils.directory_exists("output/html"):
        raise_cli_error(f"""
        The directory `output/html` does not exist.
        Maybe try `pretext build` first?
        """)
    shutil.rmtree("docs",ignore_errors=True)
    shutil.copytree("output/html","docs")
    log.info("Use these instructions if your project isn't already set up with Git and GitHub:")
    log.info("https://docs.github.com/en/github/importing-your-projects-to-github/adding-an-existing-project-to-github-using-the-command-line")
    log.info("")
    log.info("Be sure your repo on GitHub is set to publish from the `docs` subdirectory:")
    log.info("https://docs.github.com/en/github/working-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site")
    log.info("")
    log.info("Once all the above is satisifed, run the following command to update your repository and publish your built HTML on the internet:")
    log.info("git add docs; git commit -m 'publish updated HTML'; git push")

## pretext debug
# @main.command(short_help="just for testing")
# def debug():
#     import os
#     from . import static, document, utils
#     log.info("This is just for debugging and testing new features.")
#     static_dir = os.path.dirname(static.__file__)
#     xslfile = os.path.join(static_dir, 'xsl', 'pretext-html.xsl')
#     print(xslfile)
