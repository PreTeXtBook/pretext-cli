from lxml import etree

doc = etree.Element("pretext")
article = etree.SubElement(doc,"article")
p = etree.SubElement(article,"p")
p.text = "Hello PreTeXt World!"
print(etree.tostring(doc))
