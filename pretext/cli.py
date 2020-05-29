import click

#  Click command-line interface
@click.group()
def main():
    pass

@click.command()
def new():
    from . import new
    new()
main.add_command(new)