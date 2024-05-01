from plasTeX.Renderers.PageTemplate import Renderer as _Renderer
from plasTeX.TeX import TeX
from pathlib import Path
import re
import logging

log = logging.getLogger("ptxlogger")


class Pretext(_Renderer):
    """Renderer for the PreTeXt XML format"""

    fileExtension = ".ptx"

    def processFileContent(self, document, s):
        s = _Renderer.processFileContent(self, document, s)

        # Remove empty paragraphs
        s = re.compile(r"<p>\s*</p>", re.I).sub(r"", s)

        # Fix fancy quotes
        s = re.compile(r"“(.*?)”", re.I).sub(r"<q>\1</q>", s)
        s = re.compile(r"‘(.*?)’", re.I).sub(r"<sq>\1</sq>", s)

        # Fix strange apostrophes
        s = s.replace("’", "'")

        return s


Renderer = Pretext


def convert(input_file: Path, output: Path):
    log.info(f"Converting {input_file} to {output}")

    def getLines(input_file: Path):
        with open(input_file, "r") as f:
            lines = str()
            line = f.readline()
            while line:
                if line.strip().startswith("\\input") or line.strip().startswith(
                    "\\include"
                ):
                    inner_file = (
                        input_file.parent / line[line.find("{") + 1 : line.find("}")]
                    )
                    lines = lines + "\n" + getLines(inner_file) + "\n"
                else:
                    lines += line
                line = f.readline()
            return lines

    tex = TeX()
    tex.input(getLines(input_file))
    doc = tex.parse()

    tex.ownerDocument.config["files"]["split-level"] = 1
    tex.ownerDocument.config["files"][
        "filename"
    ] = "main $name-[$id, $title, $ref, sect$num(4)]"

    renderer = Renderer()
    renderer.render(doc)

    # shutil.move('test.xml', output)
    log.info("\nConversion complete")
