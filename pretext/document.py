from lxml import etree as ET
from slugify import slugify

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

def new(title_string):
    pretext = ET.Element("pretext")
    docinfo = ET.SubElement(pretext,"docinfo")
    macros = ET.SubElement(docinfo,"macros")
    macros.text = "\\newcommand{\\foo}{bar}"
    lip = ET.SubElement(docinfo,"latex-image-preamble")
    lip.text = "\\usepackage{tikz}"
    doc = ET.SubElement(pretext, "book")
    doc.set(XML_ID,slugify(title_string))
    title = ET.SubElement(doc,"title")
    title.text = title_string
    return ET.ElementTree(pretext)

def add_chapter(pretext,title_string):
    book = pretext.xpath("//book")[0]
    chapter = ET.SubElement(book,"chapter")
    chapter.set(XML_ID,slugify(title_string))
    title = ET.SubElement(chapter,"title")
    title.text = title_string

def publisher():
    from . import static
    return ET.parse(static.filepath("publisher.ptx"))
