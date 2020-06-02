from lxml import etree as ET

from . import static, document

# To access static files
try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources #backported package

def create_new_pretext_source(project_path,title,doc_type):
    ensure_directory(project_path)
    ensure_directory(f"{project_path}/source")
    document.new(title,doc_type).write(
        f"{project_path}/source/main.ptx",
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
    document.publisher().write(
        f"{project_path}/publisher.ptx",
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
    with open(f"{project_path}/.gitignore", mode='w') as gitignore:
        print("output", file=gitignore)
    with open(f"{project_path}/README.md", mode='w') as readme:
        print(f"# {title}", file=readme)
        print("", file=readme)
        print("Authored with [PreTeXt](https://pretextbook.org).", file=readme)

def build_html(ptxfile,output,stringparams):
    import os
    # from pathlib import Path
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = get_static_path('pretext-html.xsl')
    # create output directories and move there.
    # output = os.path.abspath(output)
    ensure_directory(output)
    os.chdir(output)  # change to output dir.
    ensure_directory('knowl')
    ensure_directory('images')
    # transform ptx using xsl:
    xsltproc(xslfile, ptxfile, stringparams)


def build_latex(ptxfile,output,stringparams):
    import os
    # import sys
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = get_static_path('pretext-latex.xsl')
    #create output directory
    # output = os.path.abspath(output)
    ensure_directory(output)
    os.chdir(output)
    # Do the xsltproc equivalent:
    # params = {"latex.font.size": "'20pt'"}
    xsltproc(xslfile, ptxfile, stringparams, outfile='main.tex')

    
def directory_exists(path):
    import os
    return os.path.exists(path)

def ensure_directory(path):
    import os
    # create directory at path if it doesn't exist:
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


# This gets the path to the "static" files in our distribution.  Eventually, allow for specification of alternative (mathbook/dev) distribution.
def get_static_path(file):
    with pkg_resources.path(static, file) as p:
        static_file = str(p.resolve())
    # import os.path  # abspath(), split()
    # # full path to module itself
    # ptx_path = os.path.abspath(__file__)
    # print(ptx_path)
    # # get directory:
    # module_dir, _ = os.path.split(ptx_path)
    # print(module_dir)
    # static_dir = os.path.join(module_dir, "static")
    return static_file

# This start of a utility function to replicate the tasks for xsltproc.
# TODO: add string params.  Here stringparams defaults to an empty dictionary.
def xsltproc(xslfile, xmlfile, stringparams={}, outfile=None):
    dom = ET.parse(xmlfile)
    try:
        dom.xinclude()
    except:
        print('there was an error with xinclude')
    print('Read in xsl file at', xslfile)
    xslt = ET.parse(xslfile)
    print('Load the transform')
    transform = ET.XSLT(xslt)
    print('Transform the source')
    newdom = transform(dom, **stringparams)
    print(transform.error_log)
    if outfile:
        print('writing output to file specified')
        with open(outfile, "w") as fh:
            fh.write(str(newdom))
