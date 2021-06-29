import click
import click_config_file
import click_logging
import json
from lxml import etree as ET
import logging
import os
import shutil
from slugify import slugify
import socketserver
import socket
import subprocess
import os, zipfile, requests, io
import tempfile, shutil
from . import utils, static
from . import version as cli_version
from . import document, project, utils, core
from . import build as builders
# from .static.pretext import pretext as ptxcore


log = logging.getLogger('ptxlogger')
click_logging.basic_config(log)

# config file default name:
config_file = '.ptxconfig'

#Two config file options to reuse on subcommands.
config_file_option = click_config_file.configuration_option(implicit="False", default=config_file, expose_value=True, help="Read options from configuration FILE specified.  [default: .ptxconfig]  Use `--config None` to run with standard default options.")

save_config_option = click.option('-sc', '--save-config', is_flag=True, default=False, help='save any options provided to local configuration file, specified with --config (or default ".ptxconfig")')



def raise_cli_error(message):
    raise click.UsageError(" ".join(message.split()))


#  Click command-line interface
@click.group()
# Allow a verbosity command:
@click_logging.simple_verbosity_option(log)
# @click.option('--silent', is_flag=True, help="suppress basic feedback")
# @click.option('--verbose', is_flag=True, help="show debug info")
@click.version_option(cli_version(),message=cli_version())
# @click_config_file.configuration_option()
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
    click.echo(f"Generating new PreTeXt project in `{directory_fullpath}` using `{template}` template.")
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
    click.echo(f"Success! Open `{directory_fullpath}/source/main.ptx` to edit your document")
    click.echo(f"Then try to `pretext build` and `pretext view` from within `{directory_fullpath}`.")

# pretext build
@main.command(short_help="Build specified target")
@click.argument('format', default='html',
              type=click.Choice(['html', 'latex', 'diagrams', 'all'], case_sensitive=False))
@click.option('-i', '--input', 'source', type=click.Path(), default='source/main.ptx', show_default=True,
              help='Path to main *.ptx file')
@click.option('-o', '--output', type=click.Path(), default='output', show_default=True,
              help='Path to main output directory')
@click.option('-p', '--publisher', type=click.Path(), default=None, help="Publisher file name, with path relative to base folder")
@click.option('--param', multiple=True, help="""
              Define a stringparam to use during processing. Usage: pretext build --param foo:bar --param baz:woo
""")
@click.option('-d', '--diagrams', is_flag=True, help='Regenerate images coded in source (latex-image, etc) using pretext script')
@click.option('-df', '--diagrams-format', default='svg', type=click.Choice(['svg', 'pdf', 'eps', 'tex'], case_sensitive=False), help="Specify output format for generated images (svg, png, etc).") # Add back in 'png' and 'all' when png works on Windows.
@click.option('-w', '--webwork', is_flag=True, default=False, help='Reprocess WeBWorK exercises, creating fresh webwork-representations.ptx file')
@click.option('--pdf', is_flag=True, help='Compile LaTeX output to PDF using commandline pdflatex')

@config_file_option
@save_config_option
def build(format, source, output, param, publisher, webwork, diagrams, diagrams_format, pdf, config, save_config):
    """
    Process PreTeXt files into specified format.

    For html, images coded in source (latex-image, etc) are only processed using the --diagrams option.

    If the project included WeBWorK exercises, these must be processed using the --webwork option.
    """
    # Remember options in local configfile when requested:
    if save_config:
        utils.write_config(config, source=source, output=output, param=param, publisher=publisher)
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
            raise ValueError('Publisher file ({}) does not exist'.format(stringparams['publisher']))
        stringparams['publisher'] = stringparams['publisher'].replace(os.sep, '/')
    # if user supplied output path, respect it:
    # otherwise, use defaults.  TODO: move this to a config file
    output = os.path.abspath(output)
    latex_output = os.path.join(output, "latex")
    html_output = os.path.join(output, "html")
    # set up source (input) and output as absolute paths
    source = os.path.abspath(source)
    latex_output = os.path.abspath(latex_output)
    html_output = os.path.abspath(html_output)
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
            print("No server name, {}.  Using default https://webwork-ptx.aimath.org".format(root_cause))
            server_params = "https://webwork-ptx.aimath.org"
        builders.webwork(source, webwork_output, stringparams, server_params)
    if diagrams or format=='diagrams':
        builders.diagrams(source,html_output,stringparams,diagrams_format)
    else:
        source_xml = ET.parse(source)
        source_xml.xinclude()
        if source_xml.find("//latex-image") is not None or source_xml.find("//sageplot") is not None:
            print("Warning: <latex-image/> or <sageplot/> in source, but will not be (re)built. Run pretext build diagrams if updates are needed.")
    if format=='html' or format=='all':
        builders.html(source,html_output,stringparams)
    if format=='latex' or format=='all':
        builders.latex(source,latex_output,stringparams)
        if pdf:
            with utils.working_directory(latex_output):
                subprocess.run(['pdflatex','main.tex'])

# pretext view
@main.command(short_help="Preview built PreTeXt documents in your browser.")
@click.option('--directory', type=click.Path(), default="output", show_default=True,
             help="Directory containing built PreTeXt documents.")
@click.option(
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
    '--port',
    default=8000,
    show_default=True,
    help="""
    Choose which port to use for the local server.
    """)
@config_file_option
@save_config_option
def view(directory,access,port,config,save_config):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    """

    # Remember options in local configfile when requested:
    if save_config:
        utils.write_config(config, directory=directory, access=access, port=port)

    directory = os.path.abspath(directory)
    if not utils.directory_exists(directory):
        raise_cli_error(f"""
        The directory `{directory}` does not exist.
        Maybe try `pretext build` first?
        """)
    binding = "localhost" if (access=='private') else "0.0.0.0"
    if access=='cocalc':
        project_id = json.loads(open('/home/user/.smc/info.json').read())['project_id']
        url = f"https://cocalc.com/{project_id}/server/{port}/"
    elif access=='public':
        url = f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        url = f"http://{binding}:{port}"
    Handler = utils.NoCacheHandler
    with socketserver.TCPServer((binding, port), Handler) as httpd:
        os.chdir(directory)
        click.echo(f"Your documents may be previewed at {url}")
        click.echo("Use [Ctrl]+[C] to halt the server.")
        httpd.allow_reuse_address = True
        httpd.serve_forever()

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
    click.echo("Use these instructions if your project isn't already set up with Git and GitHub:")
    click.echo("https://docs.github.com/en/github/importing-your-projects-to-github/adding-an-existing-project-to-github-using-the-command-line")
    click.echo("")
    click.echo("Be sure your repo on GitHub is set to publish from the `docs` subdirectory:")
    click.echo("https://docs.github.com/en/github/working-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site")
    click.echo("")
    click.echo("Once all the above is satisifed, run the following command to update your repository and publish your built HTML on the internet:")
    click.echo("git add docs; git commit -m 'publish updated HTML'; git push")

## pretext debug
# @main.command(short_help="just for testing")
# def debug():
#     import os
#     from . import static, document, utils
#     click.echo("This is just for debugging and testing new features.")
#     static_dir = os.path.dirname(static.__file__)
#     xslfile = os.path.join(static_dir, 'xsl', 'pretext-html.xsl')
#     print(xslfile)
