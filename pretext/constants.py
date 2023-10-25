import typing as t

NEW_TEMPLATES = ["book", "article", "demo", "hello", "slideshow"]

FORMATS = ["html", "pdf", "latex", "epub", "kindle", "braille", "webwork", "custom"]

# Give list of assets that each build format requires.
ASSETS_BY_FORMAT = {
    "html": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "codelens",
        "datafile",
    ],
    "pdf": [
        "webwork",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
    ],
    "latex": [
        "webwork",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
    ],
    "epub": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
    ],
    "kindle": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
    ],
    "braille": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
    ],
    "webwork": [
        "webwork",
    ],
    "custom": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
    ],
}

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

PROJECT_RESOURCES = [
    "project.ptx",
    "codechat_config.yaml",
    ".gitignore",
    ".devcontainer.json",
    "requirements.txt",
]
