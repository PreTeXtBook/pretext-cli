import typing as t

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
    "youtube": ["youtube", "play-button", "qrcode"],
    "interactive": ["preview", "qrcode"],
    "codelens": ["trace"],
    "datafile": ["datafile"],
}

ASSET_FORMATS: t.Dict[str, t.Dict[str, t.List[str]]] = {
    "pdf": {
        "asymptote": ["pdf"],
        "latex-image": [],
        "sageplot": ["pdf", "png"],
    },
    "latex": {
        "asymptote": ["pdf"],
        "latex-image": [],
        "sageplot": ["pdf", "png"],
    },
    "html": {
        "asymptote": ["html"],
        "latex-image": ["svg"],
        "sageplot": ["html", "svg"],
    },
    "runestone": {
        "asymptote": ["html"],
        "latex-image": ["svg"],
        "sageplot": ["html", "svg"],
    },
    "epub": {
        "asymptote": ["svg"],
        "latex-image": ["svg"],
        "sageplot": ["svg"],
    },
    "kindle": {
        "asymptote": ["png"],
        "latex-image": ["png"],
        "sageplot": ["png"],
    },
    "braille": {
        "asymptote": ["all"],
        "latex-image": ["all"],
        "sageplot": ["all"],
    },
    "custom": {
        "asymptote": ["all"],
        "latex-image": ["all"],
        "sageplot": ["all"],
    },
}
