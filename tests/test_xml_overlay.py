from pretext.config import xml_overlay
import typing as t
from lxml import etree as ET

# Allow for importing importing directly in tests functions in the development tree.
# Take from https://stackoverflow.com/questions/16981921/relative-imports-in-python-3
import sys
import os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../')

# Because of the fiddling with paths above, we do an "absolute" import instead of a relative one.


def test_xml_overlay():
    root = ET.Element("root")
    overlay = xml_overlay.ShadowXmlDocument()
    overlay.upsert_node_or_attribute("a.b", "Value!")
    overlay.upsert_node_or_attribute("a.b@fuzz", "mom")
    overlay.upsert_node_or_attribute("a.b@baz", "dad")
    overlay.upsert_node_or_attribute("a.b.c", "Child val")
    messages = overlay.overlay_tree(root)

    assert ET.tostring(
        root, encoding=str) == '<root><a><b fuzz="mom" baz="dad">Value!<c>Child val</c></b></a></root>'
    assert messages == ['NODE_ADDED with XML path a', 'NODE_ADDED with XML path a.b', "ATTRIBUTE_ADDED 'mom' at XML path 'a.b'", "ATTRIBUTE_ADDED 'dad' at XML path 'a.b'",
                        "TEXT_ADDED ''Value!'' at XML path 'a.b'", 'NODE_ADDED with XML path a.b.c', "TEXT_ADDED ''Child val'' at XML path 'a.b.c'"]

    root = ET.fromstring('<root><a><b xxx="yyy" /></a><c>Hi there</c></root>')
    overlay = xml_overlay.ShadowXmlDocument()
    overlay.upsert_node_or_attribute("a.b@xxx", "zzz")
    messages = overlay.overlay_tree(root)
    assert ET.tostring(
        root, encoding=str) == '<root><a><b xxx="zzz"/></a><c>Hi there</c></root>'
    assert messages == ["ATTRIBUTE_CHANGED 'yyy' to 'zzz' at XML path 'a.b'"]

    # A change should be applied to all instances of an element
    root = ET.fromstring('<root><a></a><a></a></root>')
    overlay = xml_overlay.ShadowXmlDocument()
    overlay.upsert_node_or_attribute("a.b@xxx", "zzz")
    messages = overlay.overlay_tree(root)
    assert ET.tostring(
        root, encoding=str) == '<root><a><b xxx="zzz"/></a><a><b xxx="zzz"/></a></root>'