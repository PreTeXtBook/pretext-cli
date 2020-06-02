from lxml import etree as ET
from . import static

def new(title,doc_type='book'):
    doc = ET.parse(static.filepath(f"{doc_type}.ptx"))
    doc.xpath('//book/title|article/title')[0].text = title
    return doc

def publisher():
    return ET.parse(static.filepath("publisher.ptx"))
