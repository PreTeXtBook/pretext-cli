from lxml import etree as ET
from pathlib import Path

# To access static files
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to python<3.7 `importlib_resources`.
    import importlib_resources as pkg_resources
from . import static

def new_pretext_document(doc_title="My Great Book!",doc_type="book"):
    doc = ET.parse(pkg_resources.open_text(static, doc_type+'.ptx'))
    doc.xpath('//book|article/title')[0].text = doc_title
    return doc

def create_new_pretext_source(doc,doc_path):
    Path(doc_path).mkdir(exist_ok=True)
    Path(doc_path+"/source").mkdir(exist_ok=True)
    doc.write(
        doc_path+"/source/main.ptx",
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
