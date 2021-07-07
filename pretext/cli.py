import click
import click_logging
import json
from lxml import etree as ET
import logging
import sys
import shutil
import socket
import subprocess
import os, zipfile, requests, io
import tempfile, shutil
import git
from . import utils, static
from . import version as cli_version
from . import build as builder
from .static.pretext import pretext as core
from .project import Target,Project


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
@click.option('-f', '--format', type=click.Choice(['html','latex','pdf']),
              help='Output format to build.')
@click.option('-i', '--input', 'source', type=click.Path(),
              help='Path to main *.ptx file')
@click.option('-o', '--output', type=click.Path(),
              help='Path to main output directory')
@click.option('-p', '--publication', type=click.Path(), default=None,
              help="Path to publication *.ptx file")
@click.option('--stringparam', nargs=2, multiple=True, help="""
              Define a stringparam to use during processing.
              Usage: pretext build --stringparam foo bar --stringparam baz woo
              """)
@click.option('-d', '--diagrams', is_flag=True, help='Regenerate images coded in source (latex-image, etc) using pretext script')
@click.option('-df', '--diagrams-format', default='svg', type=click.Choice(['svg', 'png', 'pdf', 'eps', 'tex', 'all'], case_sensitive=False), help="Specify output format for generated images (svg, png, etc).") # Add back in 'png' and 'all' when png works on Windows.
@click.option('-w', '--webwork', is_flag=True, default=False, help='Reprocess WeBWorK exercises, creating fresh webwork-representations.ptx file')
@click.option('-oa', '--only-assets', is_flag=True, default=False, help="Produce requested diagrams (-d) or webwork (-w) but not main build target (useful for large projects that only need to update assets)")
@click.option('--pdf', is_flag=True, help='Compile LaTeX output to PDF using commandline pdflatex')
def build(target, format, source, output, stringparam, publication, webwork, diagrams, diagrams_format, only_assets, pdf):
    """
    Process PreTeXt files into specified format.

    For html, images coded in source (latex-image, etc) are only processed using the --diagrams option.

    If the project included WeBWorK exercises, these must be processed using the --webwork option.
    """
    target_name = target
    # set up stringparams as dictionary:
    if len(stringparam) > 0:
        stringparams = {p[0] : p[1] for p in stringparam}
    else:
        stringparams = None
    if utils.project_path() is None:
        log.warning(f"No project.ptx manifest was found. Run `pretext init` to generate one.")
        log.warning("Continuing using commandline arguments.")
        if publication is None:
              pass
        target = Target(name=format,format=format,source=source,output_dir=output,
                        publication=publication,stringparams=stringparams)
        project = Project(targets=[target])
    else:
        project = Project()
        if target_name is None:
            log.info(f"Since no build target was supplied, the first target of the "+
                     "project.ptx manifest will be built.")
        target = project.target(name=target_name)
        if target is None:
            log.critical("Build target could not be found in project.ptx manifest.")
            log.critical("Exiting without completing task.")
            return
        #overwrite target with commandline arguments, update project accordingly
        target = Target(xml_element=target.xml_element(),
                        format=format,source=source,output_dir=output,
                        publication=publication,stringparams=stringparams)
        project = Project(xml_element=project.xml_element(),targets=[target])
    project.build(target_name,webwork,diagrams,diagrams_format,only_assets)

# pretext view
@main.command(short_help="Preview built PreTeXt documents in your browser.")
@click.argument('target', required=False)
@click.option(
    '-a',
    '--access',
    type=click.Choice(['public', 'private'], case_sensitive=False),
    default='private',
    show_default=True,
    help="""
    Choose whether or not to allow other computers on your local network
    to access your documents using your IP address. (Ignored when used
    in CoCalc, which works automatically.)
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
    '-d',
    '--directory',
    type=click.Path(),
    help="""
    Serve files from provided directory
    """)
@click.option('-w', '--watch', is_flag=True, help="""
    Watch the status of source files and
    automatically rebuild target when changes
    are made. Only supports HTML-format targets, and
    only recommended for smaller projects.
    """)
def view(target,access,port,directory,watch):
    """
    Starts a local server to preview built PreTeXt documents in your browser.
    TARGET is the name of the <target/> defined in `project.ptx`.
    """
    target_name=target
    if directory is not None:
        utils.run_server(directory,access,port)
        return
    else:
        project = Project()
        target = project.target(name=target_name)
    if target is not None:
        project.view(target_name,access,port,watch)
    else:
        log.error(f"Target `{target_name}` could not be found.")

# pretext publish
@main.command(short_help="Prepares project for publishing on GitHub Pages.")
@click.argument('target', required=False)
def publish(target):
    """
    Automates HTML publication of [TARGET] on GitHub Pages to make
    the built document available to the general public.
    Requires that your project is under Git version control
    using an `origin` remote
    properly configured with GitHub and GitHub Pages. Pubilshed
    files will live in `docs` subdirectory of project.
    """
    target_name = target
    project = Project()
    project.publish(target_name)

## pretext debug
# @main.command(short_help="just for testing")
# def debug():
#     import os
#     from . import static, document, utils
#     log.info("This is just for debugging and testing new features.")
#     static_dir = os.path.dirname(static.__file__)
#     xslfile = os.path.join(static_dir, 'xsl', 'pretext-html.xsl')
#     print(xslfile)
