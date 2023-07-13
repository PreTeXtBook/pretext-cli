import typing as t
import pydantic_xml as pxml
from .. import types as pt  # PreTeXt types


class StringParamXml(pxml.BaseXmlModel, tag="stringparam"):
    key: str = pxml.attr()
    value: str = pxml.attr()


class TargetXml(pxml.BaseXmlModel, tag="target"):
    name: str = pxml.attr()
    format: pt.Format = pxml.attr()
    source: t.Optional[str] = pxml.attr()
    publication: t.Optional[str] = pxml.attr()
    output: t.Optional[str] = pxml.attr()
    site: t.Optional[str] = pxml.attr()
    xsl: t.Optional[str] = pxml.attr()
    latex_engine: t.Optional[pt.LatexEngine] = pxml.attr(name="latex-engine")
    braille_mode: t.Optional[pt.BrailleMode] = pxml.attr(name="braille-mode")
    compression: t.Optional[pt.Compression] = pxml.attr()
    stringparams: t.List[StringParamXml] = pxml.element(tag="stringparam", default=[])


class ProjectXml(pxml.BaseXmlModel, tag="project"):
    ptx_version: t.Literal["2"] = pxml.attr(name="ptx-version")
    source: t.Optional[str] = pxml.attr()
    publication: t.Optional[str] = pxml.attr()
    output: t.Optional[str] = pxml.attr()
    site: t.Optional[str] = pxml.attr()
    xsl: t.Optional[str] = pxml.attr()
    targets: t.List[TargetXml] = pxml.wrapped("targets", pxml.element(tag="target"))


class ExecutablesXml(pxml.BaseXmlModel, tag="executables"):
    latex: t.Optional[str] = pxml.attr()
    pdflatex: t.Optional[str] = pxml.attr()
    xelatex: t.Optional[str] = pxml.attr()
    pdfsvg: t.Optional[str] = pxml.attr()
    asy: t.Optional[str] = pxml.attr()
    sage: t.Optional[str] = pxml.attr()
    pdfpng: t.Optional[str] = pxml.attr()
    pdfeps: t.Optional[str] = pxml.attr()
    node: t.Optional[str] = pxml.attr()
    liblouis: t.Optional[str] = pxml.attr()


class LegacyTargetXml(pxml.BaseXmlModel, tag="target"):
    name: str = pxml.attr()
    pdf_method: t.Optional[str] = pxml.attr(name="pdf-method")
    format: str = pxml.element()
    source: str = pxml.element()
    publication: str = pxml.element()
    output_dir: str = pxml.element(tag="output-dir")
    output_filename: t.Optional[str] = pxml.element(tag="output-filename")
    site: t.Optional[str] = pxml.element()
    xsl: t.Optional[str] = pxml.element()
    stringparams: t.List[StringParamXml] = pxml.element(tag="stringparam", default=[])


class LegacyExecutablesXml(pxml.BaseXmlModel, tag="executables"):
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


class LegacyProjectXml(pxml.BaseXmlModel, tag="project"):
    targets: t.List[LegacyTargetXml] = pxml.wrapped(
        "targets", pxml.element(tag="target")
    )
    executables: LegacyExecutablesXml = pxml.element()
