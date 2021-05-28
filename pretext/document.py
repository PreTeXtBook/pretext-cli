from lxml import etree as ET
from slugify import slugify
from .utils import nstag, NSMAP

def new(title_string):
    pretext = ET.Element(
        "pretext",
        nsmap=NSMAP
    )
    docinfo = ET.SubElement(pretext,"docinfo")
    macros = ET.SubElement(docinfo,"macros")
    macros.text = "\\newcommand{\\foo}{bar}"
    lip = ET.SubElement(docinfo,"latex-image-preamble")
    lip.text = "\\usepackage{tikz}"
    doc = ET.SubElement(pretext, "book")
    doc.set(nstag("xml","id"),slugify(title_string))
    doc.set(nstag("xml","lang"),"en-US")
    title = ET.SubElement(doc,"title")
    title.text = title_string
    return ET.ElementTree(pretext)

def add_chapter(pretext,title_string):
    book = pretext.xpath("//book")[0]
    chapter = ET.SubElement(book,"chapter")
    chapter.set(nstag("xml","id"),slugify(title_string))
    title = ET.SubElement(chapter,"title")
    title.text = title_string

def publisher():
    from . import static
    return ET.parse(static.filepath("publisher.ptx"))
