import click
import click_config_file
from . import utils
from . import version as cli_version

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
@click.option('-v', '--verbose', count=True, help="-v for basic feedback; -vv for debug info")
@click.version_option(cli_version(),message=cli_version())
# @click_config_file.configuration_option()
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
@click.option('--directory', type=click.Path(),
              help="Directory to create/use for the project. Defaults to "+
              "a subdirectory of the current path based on book title.")
@click.option('--chapter', multiple=True, help="Provide one or more chapter titles.")
@click.option('-i', '--interactive', is_flag=True, default=False, help="Interactively requests names of book chapters.")
def new(title,directory,chapter,interactive):
    """
    Creates a subdirectory with the files needed to author a PreTeXt document.

    Usage:
    pretext new "My Great Book!"
    """
    from . import document, project
    from slugify import slugify
    if not(directory):
        if slugify(title):
            directory = slugify(title)
        else:
            directory = 'my-book'
    click.echo(f"Generating new PreTeXt project in `{directory}`.")
    pretext = document.new(title)
    chapter = list(chapter)
    if interactive:
        setting_chapters = True
        current_chapter = len(chapter)+1
        while setting_chapters:
            chapter.append(click.prompt(f"Provide the title for Chapter {current_chapter}"))
            setting_chapters = click.confirm('Do you want to name another chapter?')
            current_chapter += 1
    elif not(chapter):
        chapter = ["My First Chapter"]
    for c in chapter:
        document.add_chapter(pretext,c)
    project.write(pretext, directory)
    # TODO: Set options in local configfile:
    # utils.write_config(config_file, source=source,
    #                    output=output, param=param, publisher=publisher)

# pretext build
@main.command(short_help="Build specified format target")
@click.argument('format', default='html',
              type=click.Choice(['html', 'latex', 'all'], case_sensitive=False))
#The following option is redundant; we already have lots of options in the help.
# @click.option('--format', default='html', show_default=True, help="Sets which format to build", type=click.Choice(['html', 'latex', 'all'], case_sensitive=False))
@click.option('-i', '--input', 'source', type=click.Path(), default='source/main.ptx', show_default=True,
              help='Path to main *.ptx file')
@click.option('-o', '--output', type=click.Path(), default='output', show_default=True,
              help='Path to main output directory')
@click.option('-p', '--publisher', type=click.Path(), default=None, help="Publisher file name, with path relative to base folder")
@click.option('--param', multiple=True, help="""
              Define a stringparam to use during processing. Usage: pretext build --param foo:bar --param baz:woo
""")
@click.option('-d', '--diagrams', is_flag=True, help='Regenerate images coded in source (latex-image, etc) using pretext script')
@click.option('-w', '--webwork', is_flag=True, default=False, help='Reprocess WeBWorK exercises, creating fresh webwork-representations.ptx file')

@config_file_option
@save_config_option
def build(format, source, output, param, publisher, webwork, diagrams, config, save_config ):
    """
    Process PreTeXt files into specified format.

    For html, images coded in source (latex-image, etc) are only processed using the --diagrams option.

    If the project included WeBWorK exercises, these must be processed using the --webwork option.
    """
    import os
    # Remember options in local configfile when requested:
    if save_config:
        utils.write_config(config, source=source, output=output, param=param, publisher=publisher)
    # from . import utils
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
    from . import build
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
        build.webwork(source, webwork_output, stringparams, server_params)
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
    import os
    from . import utils

    # Remember options in local configfile when requested:
    if save_config:
        utils.write_config(config, directory=directory, access=access, port=port)

    directory = os.path.abspath(directory)
    if not utils.directory_exists(directory):
        raise_cli_error(f"""
        The directory `{directory}` does not exist.
        Maybe try `pretext build` first?
        """)
    import http.server, socketserver, socket
    binding = "localhost" if (access=='private') else "0.0.0.0"
    Handler = http.server.SimpleHTTPRequestHandler
    if access=='cocalc':
        import json
        project_id = json.loads(open('/home/user/.smc/info.json').read())['project_id']
        url = f"https://cocalc.com/{project_id}/server/{port}/"
    elif access=='public':
        url = f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        url = f"http://{binding}:{port}"
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
    from . import utils
    if not utils.directory_exists("output/html"):
        raise_cli_error(f"""
        The directory `output/html` does not exist.
        Maybe try `pretext build` first?
        """)
    import shutil
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
