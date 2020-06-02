import click

def raise_cli_error(message):
    raise click.UsageError(" ".join(message.split()))

#  Click command-line interface
@click.group()
def main():
    """
    Command line tools for quickly creating, authoring, and building
    PreTeXt documents.
    """

    
# pretext new
@click.command(short_help="Provision a new PreTeXt document.")
@click.argument('title', required=True)
@click.argument('project_path', required=False)
@click.option(
    '--book/--article', 
    default=True,
    help="""
    Creates a PreTeXt book (default setting) or article.
    """
)
def new(title,book,project_path):
    """
    Creates a subdirectory with the files needed to author a PreTeXt document.
    Requires choosing a TITLE. Optionally takes a PROJECT_PATH, otherwise
    the project will be generated in a subfolder based upon the title.

    Example:
    pretext new "My Great Book!"
    """
    from . import project
    from slugify import slugify
    if book:
        doc_type="book"
    else:
        doc_type="article"
    if not(project_path):
        if slugify(title):
            project_path = slugify(title)
        else:
            project_path = doc_type
    click.echo(f"Generating new PreTeXt project in `{project_path}`.")
    project.new(
        title,
        doc_type,
        project_path
    )
main.add_command(new)


# pretext build
@click.command(short_help="Build specified format target")
# @click.option('--html', 'format', flag_value='html',default=True, help="Build document to HTML (default)")
# @click.option('--latex', 'format', flag_value='latex', help="Build document to LaTeX")
#@click.option('-a', '--all', 'format', flag_value='all', help="Build all main document formats (HTML,LaTeX)")
@click.option('-i', '--input', type=click.Path(), default='source/main.ptx',
              help='Path to main ptx file (defaults to `source/main.ptx`)')
@click.option('-o', '--output', type=click.Path(), default='./output',
              help='Define output directory path (defaults to `output`)')
@click.option('--param', multiple=True, help="""
              Define a stringparam to use during processing. Usage: pretext build --param foo=bar --param baz=woo
""")
@click.argument('format')
# @click.option('-w', '--webwork', is_flag=True, default=False, help='rebuild webwork')
# @click.option('-d', '--diagrams', is_flag=True, default=False, help='regenerate images using mbx script')
def build(format, input, output, param):
    """
    Process PreTeXt files into specified format.
    Current supported choices for FORMAT are `html`, `latex`, or `all` (for both html and latex).
    """
    stringparams = dict([p.split("=") for p in param])
    from . import build
    if format=='html' or format=='all':
        build.html(input,output,stringparams)
    if format=='latex' or format=='all':
        from . import build_latex
        build.latex(input,output,stringparams)
main.add_command(build)


# pretext view
@click.command(short_help="Preview built PreTeXt documents in your browser.")
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
main.add_command(view)
