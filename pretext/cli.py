import click
from slugify import slugify

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
    from . import new_pretext_document, create_new_pretext_source 
    create_new_pretext_source(new_pretext_document(title,"book"), slugify(title))
main.add_command(new)

@click.command(short_help="Build specified format target")
# @click.option('-t', '--target-format', default="html", help='output format (latex/html/epub)')
@click.option('-o', '--output', type=click.Path(), default='./output', help='output directory path')
# @click.option('-w', '--webwork', is_flag=True, default=False, help='rebuild webwork')
# @click.option('-d', '--diagrams', is_flag=True, default=False, help='regenerate images using mbx script')
@click.argument('format')
def build(format, output):
    """Process PreTeXt files into specified format, either html or latex."""
    if format=='html':
        from . import build_html
        build_html(output)
    elif format=='latex':
        from . import build_latex
        build_latex(output)
    else:
        click.echo('%s is not yet a supported build target' % format)
main.add_command(build)
