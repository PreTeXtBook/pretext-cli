from pathlib import Path
import shutil
import typing as t
from enum import Enum
from pydantic import ConfigDict
import pydantic_xml as pxml
from pydantic_xml.element.element import SearchMode


# To prevent circular imports, put this here instead of in `__init__`; however, it's not used in this file.
class Executables(pxml.BaseXmlModel, tag="executables"):
    model_config = ConfigDict(extra="forbid")
    latex: str = pxml.attr(default="latex")
    pdflatex: str = pxml.attr(default="pdflatex")
    xelatex: str = pxml.attr(default="xelatex")
    pdfsvg: t.Optional[str] = pxml.attr(default="pdf2svg")
    # If not specified, use a local executable if it exists; if it doesn't exist, choose `None`, which allows the generation logic to use the server instead.
    asy: t.Optional[str] = pxml.attr(default=shutil.which("asy"))
    # The same applies to Sage.
    sage: t.Optional[str] = pxml.attr(default=shutil.which("sage"))
    mermaid: str = pxml.attr(default="mmdc")
    pdfpng: t.Optional[str] = pxml.attr(default="convert")
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


class LegacyStringParam(pxml.BaseXmlModel):
    model_config = ConfigDict()
    key: str = pxml.attr()
    value: str = pxml.attr()


class LegacyTarget(pxml.BaseXmlModel, tag="target", search_mode=SearchMode.UNORDERED):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = pxml.attr()
    latex_engine: t.Optional[LatexEngine] = pxml.attr(name="pdf-method", default=None)
    format: LegacyFormat = pxml.element()
    source: str = pxml.element()
    publication: str = pxml.element()
    output_dir: Path = pxml.element(tag="output-dir")
    output_filename: t.Optional[str] = pxml.element(tag="output-filename", default=None)
    # The v1 file called this `deploy-dir`; the v2 file uses `site`.
    deploy_dir: t.Optional[str] = pxml.element(tag="deploy-dir", default=None)
    xsl: t.Optional[str] = pxml.element(default=None)
    asy_method: t.Optional[str] = pxml.element(tag="asy-method", default="server")
    stringparams: t.List[LegacyStringParam] = pxml.element(
        tag="stringparam", default=[]
    )


class LegacyExecutables(
    pxml.BaseXmlModel, tag="executables", search_mode=SearchMode.UNORDERED
):
    model_config = ConfigDict(str_strip_whitespace=True)
    latex: str = pxml.element()
    pdflatex: str = pxml.element()
    xelatex: str = pxml.element()
    pdfsvg: t.Optional[str] = pxml.element(default=None)
    asy: str = pxml.element()
    sage: str = pxml.element()
    pdfpng: t.Optional[str] = pxml.element(default=None)
    pdfeps: str = pxml.element()
    node: str = pxml.element()
    liblouis: str = pxml.element()


class LegacyProject(pxml.BaseXmlModel, tag="project", search_mode=SearchMode.UNORDERED):
    model_config = ConfigDict()
    targets: t.List[LegacyTarget] = pxml.wrapped("targets", pxml.element(tag="target"))
    executables: LegacyExecutables = pxml.element()
