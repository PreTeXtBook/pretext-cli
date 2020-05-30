from lxml import etree as ET
from slugify import slugify
from pathlib import Path

# To access static files
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to python<3.7 `importlib_resources`.
    import importlib_resources as pkg_resources
from . import static

def new(book_title="My Great Book!"):
    '''
    Generates scaffolding for a PreTeXt book.
    '''
    doc = ET.parse(pkg_resources.open_text(static, 'book.ptx'))
    doc.xpath('//book/title')[0].text = book_title
    book_slug = slugify(book_title)
    Path(book_slug).mkdir(exist_ok=True)
    Path(book_slug+"/source").mkdir(exist_ok=True)
    doc.write(
        book_slug+"/source/main.ptx",
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
