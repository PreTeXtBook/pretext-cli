from lxml import etree as ET

# To access static files
try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources #backported package
from . import static

def new_pretext_document(title,doc_type):
    doc = ET.parse(pkg_resources.open_text(static, f"{doc_type}.ptx"))
    doc.xpath('//book/title|article/title')[0].text = title
    return doc

def create_new_pretext_source(project_path,title,doc_type):
    ensure_directory(project_path)
    ensure_directory(f"{project_path}/source")
    new_pretext_document(title,doc_type).write(
        f"{project_path}/source/main.ptx",
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

def build_html(output):
    import os
    from pathlib import Path
    ptxfile = Path('source/main.ptx')
    ptxfile = str(ptxfile.resolve())
    # with pkg_resources.path(static, 'pretext-html.xsl') as p:
    #     xslfile = str(p.resolve())
    xslfile = os.path.join(get_static_path(), "pretext-html.xsl")
    print(xslfile)
    Path(output).mkdir(parents=True, exist_ok=True)
    os.chdir(output)  # change to output dir.
    try:
        os.mkdir('knowl')
    except OSError:
        print("Creation of the directory %s failed" % 'knowl')
    else:
        print("Successfully created the directory %s " % 'knowl')
    # Path('knowl').mkdir(exist_ok=True)
    # if not os.path.exists('knowl'):
    #     os.makedirs('knowl')
    Path('images').mkdir(exist_ok=True)
    # if not os.path.exists('images'):
    #     os.makedirs('images')
    dom = ET.parse(ptxfile)
    dom.xinclude()
    xslt = ET.parse(xslfile)
    transform = ET.XSLT(xslt)
    transform(dom)

def build_latex(output):
    import os
    ptxfile = os.path.abspath('source/main.ptx')
    xslfile = os.path.join(get_static_path(), "pretext-latex.xsl")
    # Clean this up:
    try: 
        os.mkdirs(output)
    except:
        pass
    os.chdir(output)
    try: 
        os.mkdir('latex')
    except:
        pass
    os.chdir('latex')
    # Do the xsltproc equivalent:
    dom = ET.parse(ptxfile)
    dom.xinclude()
    xslt = ET.parse(xslfile)
    transform = ET.XSLT(xslt)
    newdom = transform(dom)
    outfile = open("main.tex", 'w', newline='')
    outfile.write(str(newdom))
    outfile.close()

    
def directory_exists(path):
    from pathlib import Path
    return Path(path).exists()

def ensure_directory(path):
    from pathlib import Path
    Path(path).mkdir(exist_ok=True)


# Adapted from mathbook's pretext.py.  This gets the path to the "static" files in our distribution.  Eventually, allow for specification of alternative (mathbook/dev) distribution.
def get_static_path():
    import os.path  # abspath(), split()
    # full path to module itself
    ptx_path = os.path.abspath(__file__)
    print(ptx_path)
    # get directory:
    module_dir, _ = os.path.split(ptx_path)
    print(module_dir)
    static_dir = os.path.join(module_dir, "static")
    return static_dir
