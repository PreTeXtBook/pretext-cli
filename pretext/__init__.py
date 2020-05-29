from lxml import etree as ET
from slugify import slugify
from pathlib import Path

def new(book_title="My Great Book!"):
    '''
    Generates scaffolding for a PreTeXt book.
    '''
    doc = ET.Element("pretext")
    book = ET.SubElement(doc,"book")
    title = ET.SubElement(book,"title")
    title.text = book_title
    p = ET.SubElement(book,"p")
    p.text = "Hello PreTeXt World!"
    book_slug = slugify(book_title)
    Path(book_slug).mkdir(exist_ok=True)
    Path(book_slug+"/source").mkdir(exist_ok=True)
    ET.ElementTree(doc).write(
        book_slug+"/source/main.ptx",
        pretty_print=True,
        xml_declaration=True,
        encoding="utf-8"
    )
