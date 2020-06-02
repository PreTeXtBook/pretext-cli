from lxml import etree as ET

# To access static files
try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources #backported package
from . import static

def new(title,doc_type):
    doc = ET.parse(pkg_resources.open_text(static, f"{doc_type}.ptx"))
    doc.xpath('//book/title|article/title')[0].text = title
    return doc

def publisher():
    return ET.parse(pkg_resources.open_text(static, "publisher.ptx"))
