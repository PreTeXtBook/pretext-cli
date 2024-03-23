from plasTeX.Renderers.PageTemplate import Renderer as _Renderer
from plasTeX.TeX import TeX


class Pretext(_Renderer):
    """ Renderer for the PreTeXt XML format """


Renderer = Pretext


def convert(input_file: str, output: str):
    with open(input_file, 'r') as f:
        tex = TeX()
        tex.ownerDocument.config['files']['split-level'] = -100
        tex.ownerDocument.config['files']['filename'] = output / 'test.xml'
        tex.input(f.read())
        doc = tex.parse()

        renderer = Renderer()
        renderer.render(doc)
