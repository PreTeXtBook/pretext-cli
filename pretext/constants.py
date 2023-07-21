NEW_TEMPLATES = ["book", "article", "demo", "hello", "slideshow"]

BUILD_FORMATS = [
    "html",
    "pdf",
    "latex",
    "epub",
    "kindle",  # TODO: mode of epub rather than separate format?
    "braille",
    "html-zip",  # TODO: deprecate
    "webwork-sets",  # TODO: just "webwork"
    "webwork-sets-zipped",  # TODO: deprecate
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
