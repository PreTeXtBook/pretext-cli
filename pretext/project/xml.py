import logging
from pathlib import Path
import shutil
import typing as t
from enum import Enum
from pydantic import ConfigDict, model_validator
import pydantic_xml as pxml
from pydantic_xml.element.element import SearchMode

log = logging.getLogger("ptxlogger")

# Executables that the core script once used but no longer does. They are still
# accepted (silently deleting them would make every older `executables.ptx` a
# hard parse error, since the model forbids extra attributes), but they are
# excluded from `model_dump()` and so never reach core.
DEPRECATED_EXECUTABLES = {
    "liblouis": "braille is now translated with the `louis` Python bindings",
    "pdfsvg": "PDFs are now converted with the pyMuPDF library",
    "pdfpng": "PDFs are now converted with the pyMuPDF library",
}


# To prevent circular imports, put this here instead of in `__init__`; however, it's not used in this file.
class Executables(pxml.BaseXmlModel, tag="executables"):
    """The executables the core script invokes; keep in sync with the
    `[executables]` section of the core script's `pretext.cfg`."""

    model_config = ConfigDict(extra="forbid")
    latex: str = pxml.attr(default="latex")
    pdflatex: str = pxml.attr(default="pdflatex")
    xelatex: str = pxml.attr(default="xelatex")
    # If not specified, use a local executable if it exists; if it doesn't exist, choose `None`, which allows the generation logic to use the server instead.
    asy: t.Optional[str] = pxml.attr(default=shutil.which("asy"))
    # No sage server, so we don't do the same for sage.
    sage: t.Optional[str] = pxml.attr(default="sage")
    mermaid: str = pxml.attr(default="mmdc")
    pdfeps: str = pxml.attr(default="pdftops")
    node: str = pxml.attr(default="node")
    perl: str = pxml.attr(default="perl")
    fop: str = pxml.attr(default="fop")
    # `jing` is a Java program, so this can be the name of an executable (from a
    # system package) or a command with options, e.g. `java -jar /usr/share/java/jing.jar`.
    jing: str = pxml.attr(default="jing")

    # Deprecated: see `DEPRECATED_EXECUTABLES`. `exclude=True` keeps these out of
    # `model_dump()`, which is what gets handed to core.
    liblouis: t.Optional[str] = pxml.attr(default=None, exclude=True)
    pdfsvg: t.Optional[str] = pxml.attr(default=None, exclude=True)
    pdfpng: t.Optional[str] = pxml.attr(default=None, exclude=True)

    @model_validator(mode="after")
    def warn_about_deprecated(self) -> "Executables":
        for name, reason in DEPRECATED_EXECUTABLES.items():
            if getattr(self, name) is not None:
                log.warning(
                    f'The "{name}" executable is no longer used by PreTeXt ({reason}); '
                    "you can remove it from your executables.ptx file."
                )
        return self

    @classmethod
    def from_legacy(cls, legacy: "LegacyExecutables") -> "Executables":
        """Build from a v1 manifest's `<executables>`, which names only a subset
        of the executables core needs; the rest keep their defaults."""
        return cls(
            **{
                key: value
                for key, value in legacy.model_dump().items()
                if value is not None and key in cls.model_fields
            }
        )


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


class PdfMethod(str, Enum):
    XELATEX = "xelatex"
    LATEX = "latex"
    PDFLATEX = "pdflatex"
    LUALATEX = "lualatex"
    PDF_FO = "pdf-fo"


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
    asy_method: t.Optional[str] = pxml.element(tag="asy-method", default="local")
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
    asy: str = pxml.element()
    sage: str = pxml.element()
    pdfeps: str = pxml.element()
    node: str = pxml.element()
    # Deprecated (see `DEPRECATED_EXECUTABLES`), but optional rather than absent,
    # since legacy manifests in the wild still carry these elements.
    liblouis: t.Optional[str] = pxml.element(default=None)
    pdfsvg: t.Optional[str] = pxml.element(default=None)
    pdfpng: t.Optional[str] = pxml.element(default=None)


class LegacyProject(pxml.BaseXmlModel, tag="project", search_mode=SearchMode.UNORDERED):
    model_config = ConfigDict()
    targets: t.List[LegacyTarget] = pxml.wrapped("targets", pxml.element(tag="target"))
    executables: LegacyExecutables = pxml.element()
