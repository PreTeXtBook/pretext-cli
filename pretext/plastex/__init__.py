from plasTeX.Renderers.PageTemplate import Renderer as _Renderer
from plasTeX.TeX import TeX
from pathlib import Path
import logging

log = logging.getLogger("ptxlogger")


class Pretext(_Renderer):
    """ Renderer for the PreTeXt XML format """
    fileExtension = '.ptx'


Renderer = Pretext


def convert(input_file: Path, output: Path):
    log.info(f'Converting {input_file} to {output}')

    def getLines(input_file: Path):
        with open(input_file, 'r') as f:
            lines = str()
            line = f.readline()
            print(line)
            while line:
                if line.strip().startswith("\\input") or line.strip().startswith("\\include"):
                    inner_file = input_file.parent / line[line.find("{")+1:line.find("}")]
                    lines = lines + "\n" + getLines(inner_file) + "\n"
                else:
                    lines += line
                line = f.readline()
            return lines

    tex = TeX()
    tex.input(getLines(input_file))
    doc = tex.parse()

    # tex.ownerDocument.config['files']['split-level'] = -100
    # tex.ownerDocument.config['files']['filename'] = "test.xml"
    # tex.input(f.read())

    renderer = Renderer()
    renderer.render(doc)

    # shutil.move('test.xml', output)
    log.info('\nConversion complete')
