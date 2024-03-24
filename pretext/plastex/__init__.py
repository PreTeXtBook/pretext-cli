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

    with open(input_file, 'r') as f:
        tex = TeX()
        # tex.ownerDocument.config['files']['split-level'] = -100
        # tex.ownerDocument.config['files']['filename'] = "test.xml"
        tex.input(f.read())
        doc = tex.parse()

        renderer = Renderer()
        renderer.render(doc)

    # shutil.move('test.xml', output)
    log.info('\nConversion complete')
