import typing as t
from enum import Enum
import pydantic_xml as pxml


class Executables(pxml.BaseXmlModel, tag="executables"):
    latex: str = pxml.attr(default="latex")
    pdflatex: str = pxml.attr(default="pdflatex")
    xelatex: str = pxml.attr(default="xelatex")
    pdfsvg: str = pxml.attr(default="pdf2svg")
    asy: str = pxml.attr(default="asy")
    sage: str = pxml.attr(default="sage")
    pdfpng: str = pxml.attr(default="convert")
    pdfeps: str = pxml.attr(default="pdftops")
    node: str = pxml.attr(default="node")
    liblouis: str = pxml.attr(default="file2brl")


class LegacyFormat(str, Enum):
    HTML = "html"
    HTML_ZIP = "html-zip"
    LATEX = "latex"
    PDF = "pdf"
    EPUB = "epub"
    KINDLE = "kindle"
    BRAILLE_ELECTRONIC = "braille-electronic"
    BRAILLE_EMBOSS = "braille-emboss"
    WEBWORK = "webwork-sets"
    WEBWORK_ZIPPED = "webwork-sets-zipped"
    CUSTOM = "custom"


class LatexEngine(str, Enum):
    XELATEX = "xelatex"
    LATEX = "latex"
    PDFLATEX = "pdflatex"


class StringParam(pxml.BaseXmlModel, tag="stringparam"):
    key: str = pxml.attr()
    value: str = pxml.attr()


class LegacyTarget(pxml.BaseXmlModel, tag="target", search_mode="unordered"):
    name: str = pxml.attr()
    latex_engine: t.Optional[LatexEngine] = pxml.attr(name="pdf-method")
    format: LegacyFormat = pxml.element()
    source: str = pxml.element()
    publication: str = pxml.element()
    # The v1 file called this `output-dir`; the v2 file uses just `output`.
    output: str = pxml.element(tag="output-dir")
    output_filename: t.Optional[str] = pxml.element(tag="output-filename")
    site: t.Optional[str] = pxml.element()
    xsl: t.Optional[str] = pxml.element()
    stringparams: t.List[StringParam] = pxml.element(tag="stringparam", default=[])


class LegacyExecutables(pxml.BaseXmlModel, tag="executables", search_mode="unordered"):
    latex: str = pxml.element()
    pdflatex: str = pxml.element()
    xelatex: str = pxml.element()
    pdfsvg: str = pxml.element()
    asy: str = pxml.element()
    sage: str = pxml.element()
    pdfpng: str = pxml.element()
    pdfeps: str = pxml.element()
    node: str = pxml.element()
    liblouis: str = pxml.element()


class LegacyProject(pxml.BaseXmlModel, tag="project", search_mode="unordered"):
    targets: t.List[LegacyTarget] = pxml.wrapped("targets", pxml.element(tag="target"))
    executables: LegacyExecutables = pxml.element()
