import click

#  Click command-line interface
@click.group()
def main():
    pass

@click.command()
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