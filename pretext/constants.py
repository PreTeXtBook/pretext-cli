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
    "webwork": ".//webwork[*|@*]",
    "latex-image": ".//latex-image",
    "sageplot": ".//sageplot",
    "asymptote": ".//asymptote",
    "youtube": ".//video[@youtube]",
    "codelens": ".//program[@interactive = 'codelens']",
    "datafile": ".//datafile",
    "interactive": ".//interactive",
}
ASSETS = ["ALL"] + list(ASSET_TO_XPATH.keys())

ASSET_TO_DIR = {
    "webwork": ["webwork"],
    "latex-image": ["latex-image"],
    "sageplot": ["sageplot"],
    "asymptote": ["asymptote"],
    "youtube": ["youtube", "play-button", "qr-code"],
    "interactive": ["preview", "qr-code"],
    "codelens": ["trace"],
    "datafile": ["datafile"],
}

ASSET_FORMATS = {
    "asymptote": {
        "pdf": ["pdf"],
        "latex": ["pdf"],
        "html": ["html"],
        "epub": ["svg"],
        "kindle": ["png"],
    },
    "latex-image": {
        "pdf": [],
        "latex": [],
        "html": ["svg"],
        "epub": ["svg"],
        "kindle": ["png"],
    },
    "sageplot": {
        "pdf": ["pdf", "png"],
        "latex": ["pdf", "png"],
        "html": ["html", "svg"],
        "epub": ["svg"],
        "kindle": ["png"],
    },
}
