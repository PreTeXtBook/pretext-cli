import click
from . import utils
from . import version as cli_version

def raise_cli_error(message):
    raise click.UsageError(" ".join(message.split()))


#  Click command-line interface
@click.group()
# Allow a verbosity command:
@click.option('-v', '--verbose', count=True, help="-v for basic feedback; -vv for debug info")
@click.version_option(cli_version(),message=cli_version())
def main(verbose):
    """
    Command line tools for quickly creating, authoring, and building
    PreTeXt documents.
    """
    # set verbosity:
    utils.set_verbosity(verbose)


# pretext new
@main.command(short_help="Provision a new PreTeXt document.")
@click.argument('title', default="My Great Book!")
@click.option('--project_path')
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
    click.echo(f"Generating new PreTeXt project in `{project_path}`.")
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
    project.write(pretext, project_path)


# pretext build
@main.command(short_help="Build specified format target")
@click.argument('format', default='html',
              type=click.Choice(['html', 'latex', 'all'], case_sensitive=False))
@click.option('-i', '--input', 'source', type=click.Path(), default='source/main.ptx', show_default=True,
              help='Path to main *.ptx file')
@click.option('-o', '--output', type=click.Path(),
              help='Define output directory path [default output/FORMAT]')
@click.option('--param', multiple=True, help="""
              Define a stringparam to use during processing. Usage: pretext build --param foo=bar --param baz=woo
""")
@click.option('-p', '--publisher', type=click.Path(), default=None, help="Publisher file name, with path relative to main pretext source file.")
@click.option('-d', '--diagrams', is_flag=True, help='Regenerate images using pretext script')
# @click.option('-w', '--webwork', is_flag=True, default=False, help='rebuild webwork')
def build(format, source, output, param, diagrams, publisher):
    """
    Process PreTeXt files into specified format.
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
@click.option('--directory', type=click.Path(), default="output", show_default=True,
             help="Directory containing built PreTeXt documents.")
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
    show_default=True,
    help="""
    Choose which port to use for the local server.
    """)
def view(directory, public, port):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
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
