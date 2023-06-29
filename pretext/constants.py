from pathlib import Path

NEW_TEMPLATES = ["book", "article", "demo", "hello", "slideshow"]

BUILD_FORMATS = [
    "html",
    "pdf",
    "latex",
    "epub",
    "kindle",
    "braille",
    "html-zip",
    "webwork-sets",
    "webwork-sets-zipped",
]

ASSET_TO_XPATH = {
    "webwork": "webwork",
    "latex-image": "latex-image",
    "sageplot": "sageplot",
    "asymptote": "asymptote",
    "youtube": "video[@youtube]",
    "codelens": "program[@interactive='codelens']",
    "datafile": "datafile",
    "interactive": "interactive",
}
ASSETS = ["ALL"] + list(ASSET_TO_XPATH.keys())

EXECUTABLES_DEFAULT = {
    "latex": "latex",
    "pdflatex": "pdflatex",
    "xelatex": "xelatex",
    "pdfsvg": "pdf2svg",
    "asy": "asy",
    "sage": "sage",
    "pdfpng": "convert",
    "pdfeps": "pdftops",
    "node": "node",
    "liblouis": "file2brl",
}

PROJECT_DEFAULT = {
    "path": Path(),
    "source": Path("source"),
    "publication": Path("publication"),
    "output": Path("output"),
    "site": Path("site"),
    "xsl": Path("xsl"),
    "executables": EXECUTABLES_DEFAULT,
}

TARGET_DEFAULT = {
    "source": Path("main.ptx"),
    "publication": Path("publication.ptx"),
    # "output" depends on name
    "site": None,
    "xsl": None,
    "latex_engine": "xelatex",
    "stringparams": {},
}
