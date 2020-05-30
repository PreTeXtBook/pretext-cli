import click

#  Click command-line interface
@click.group()
def main():
    """
    Command line tools for quickly creating, authoring, and building
    PreTeXt documents.
    """

@click.command(short_help="Provision a new PreTeXt document.")
@click.argument('title', required=True)
def new(title):
    """
    Creates a subdirectory with the files needed to author a PreTeXt document.
    Requires choosing a TITLE.
    
    Example:
    pretext new "My Great Book!"
    """
    from . import new
    new(title)
main.add_command(new)