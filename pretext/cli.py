import click
from slugify import slugify

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
def new(title):
    """
    Creates a subdirectory with the files needed to author a PreTeXt document.
    Requires choosing a TITLE.

    Example:
    pretext new "My Great Book!"
    """
    from . import new_pretext_document, create_new_pretext_source
    create_new_pretext_source(new_pretext_document(title, "book"),
                              slugify(title))
main.add_command(new)


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
    from . import directory_exists
    if not directory_exists(directory):
        raise_cli_error(f"""
        The directory `{directory}` does not exist.
        Maybe try `pretext build` first?
        """)
    import http.server
    import socketserver
    import os
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
