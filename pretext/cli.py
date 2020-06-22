import click
from . import utils

def raise_cli_error(message):
    raise click.UsageError(" ".join(message.split()))


#  Click command-line interface
@click.group()
# Allow a verbosity command:
@click.option('-v', '--verbose', count=True, help="-v for basic feedback; -vv for debug info")
def main(verbose):
    """
    Command line tools for quickly creating, authoring, and building
    PreTeXt documents.
    """
    # set verbosity:
    utils.set_verbosity(verbose)


# pretext new
@main.command(short_help="Display version.")
def version():
    from . import version
    click.echo(version())


# pretext new
@main.command(short_help="Provision a new PreTeXt document.")
@click.argument('title', required=True)
@click.argument('project_path', required=False)
@click.option('--chapter', multiple=True, help="Provide one or more chapter titles.")
def new(title,project_path,chapter):
    """
    Creates a subdirectory with the files needed to author a PreTeXt document.
    Requires choosing a TITLE. Optionally takes a PROJECT_PATH, otherwise
    the project will be generated in a subfolder based upon the title.

    Usage:
    pretext new "My Great Book!"
    """
    from . import document, project
    from slugify import slugify
    if not(project_path):
        if slugify(title):
            project_path = slugify(title)
        else:
            project_path = 'my-book'
    pretext = document.new(title)
    chapter = list(chapter)
    if not(chapter):
        setting_chapters = True
        current_chapter = 1
        while setting_chapters:
            chapter.append(click.prompt(f"Provide the title for Chapter {current_chapter}"))
            setting_chapters = click.confirm('Do you want to name another chapter?')
            current_chapter += 1
    for c in chapter:
        document.add_chapter(pretext,c)
    click.echo(f"Generating new PreTeXt project in `{project_path}`.")
    project.write(pretext, project_path)


# pretext build
@main.command(short_help="Build specified format target")
# @click.option('--html', 'format', flag_value='html',default=True, help="Build document to HTML (default)")
# @click.option('--latex', 'format', flag_value='latex', help="Build document to LaTeX")
#@click.option('-a', '--all', 'format', flag_value='all', help="Build all main document formats (HTML,LaTeX)")
@click.option('-i', '--input', 'source', type=click.Path(), default='source/main.ptx',
              help='Path to main *.ptx file (defaults to `source/main.ptx`)')
@click.option('-o', '--output', type=click.Path(),
              help='Define output directory path (defaults to `output`)')
@click.option('--param', multiple=True, help="""
              Define a stringparam to use during processing. Usage: pretext build --param foo=bar --param baz=woo
""")
@click.option('-p', '--publisher', type=click.Path(), default=None, help="publisher file name, with path relative to main pretext source file.")
@click.argument('format')
# @click.option('-w', '--webwork', is_flag=True, default=False, help='rebuild webwork')
@click.option('-d', '--diagrams', is_flag=True, help='regenerate images using pretext script')
def build(format, source, output, param, diagrams, publisher):
    """
    Process PreTeXt files into specified format.
    Current supported choices for FORMAT are `html`, `latex`, or `all` (for both html and latex).
    """
    import os
    # set up stringparams as dictionary:
    stringparams = dict([p.split("=") for p in param])
    # TODO: Move to config file
    if publisher:
        stringparams['publisher'] = publisher
    # if user supplied output path, respect it:
    # otherwise, use defaults.  TODO: move this to a config file
    latex_output = 'output/latex'
    html_output = 'output/html'
    if output:
        latex_output = output
        html_output = output
    # set up source (input) and output as absolute paths
    source = os.path.abspath(source)
    latex_output = os.path.abspath(latex_output)
    html_output = os.path.abspath(html_output)
    #build targets:
    from . import build
    if format=='html' or format=='all':
        if diagrams:
            build.diagrams(source,html_output,stringparams)
        build.html(source,html_output,stringparams)
    if format=='latex' or format=='all':
        build.latex(source,latex_output,stringparams)


# pretext view
@main.command(short_help="Preview built PreTeXt documents in your browser.")
@click.argument('directory', default="output")
@click.option(
    '--public/--private',
    default=False,
    help="""
    Choose whether to allow other computers on your local network
    to access your documents using your IP address. Defaults to private.
    """)
@click.option(
    '--port',
    default=8000,
    help="""
    Choose which port to use for the local server. Defaults to 8000.
    """)
def view(directory, public, port):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    Use DIRECTORY to designate the folder with your built documents (defaults
    to `output`).
    """
    import os
    directory = os.path.abspath(directory)
    from . import utils
    if not utils.directory_exists(directory):
        raise_cli_error(f"""
        The directory `{directory}` does not exist.
        Maybe try `pretext build` first?
        """)
    import http.server
    import socketserver
    binding = "0.0.0.0" if public else "localhost"
    import socket
    if public:
        url = f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        url = f"http://{binding}:{port}"
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer((binding, port), Handler) as httpd:
        os.chdir(directory)
        click.echo(f"Your documents may be previewed at {url}")
        click.echo("Use [Ctrl]+[C] to halt the server.")
        httpd.serve_forever()
