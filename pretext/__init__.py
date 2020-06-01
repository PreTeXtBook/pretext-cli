from lxml import etree as ET

# To access static files
try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources #backported package
from . import static

def new_pretext_document(title,doc_type):
    doc = ET.parse(pkg_resources.open_text(static, f"{doc_type}.ptx"))
    doc.xpath('//book|article/title')[0].text = title
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

def directory_exists(path):
    from pathlib import Path
    return Path(path).exists()

def ensure_directory(path):
    from pathlib import Path
    Path(path).mkdir(exist_ok=True)
