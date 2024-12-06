import typing as t
from pathlib import Path

NEW_TEMPLATES = ["book", "article", "course", "demo", "hello", "slideshow"]

FORMATS = [
    "html",
    "pdf",
    "latex",
    "epub",
    "kindle",
    "braille",
    "revealjs",
    "webwork",
    "custom",
]

# Give list of assets that each build format requires.  Note that myopenmath must be present for html to generate some other "static" assets, even in html.
ASSETS_BY_FORMAT = {
    "html": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "prefigure",
        "codelens",
        "datafile",
        "myopenmath",
    ],
    "pdf": [
        "webwork",
        "sageplot",
        "asymptote",
        "prefigure",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
        "mermaid",
        "myopenmath",
        "dynamic-subs",
    ],
    "latex": [
        "webwork",
        "sageplot",
        "asymptote",
        "prefigure",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
        "mermaid",
        "myopenmath",
        "dynamic-subs",
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
        "mermaid",
        "myopenmath",
        "dynamic-subs",
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
        "mermaid",
        "myopenmath",
        "dynamic-subs",
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
        "mermaid",
        "myopenmath",
        "dynamic-subs",
    ],
    "revealjs": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "prefigure",
        "codelens",
        "datafile",
        "myopenmath",
    ],
    "webwork": [
        "webwork",
    ],
    "custom": [
        "webwork",
        "latex-image",
        "sageplot",
        "asymptote",
        "prefigure",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
        "mermaid",
        "myopenmath",
        "dynamic-subs",
    ],
}

ASSET_TO_XPATH = {
    "webwork": ".//webwork[*|@*]",
    "latex-image": ".//latex-image",
    "sageplot": ".//sageplot",
    "asymptote": ".//asymptote",
    "prefigure": ".//pf:prefigure",
    "youtube": ".//video[@youtube]",
    "codelens": ".//program[@interactive = 'codelens']",
    "datafile": ".//datafile",
    "interactive": ".//interactive",
    "mermaid": ".//mermaid",
    "myopenmath": ".//myopenmath",
    "dynamic-subs": ".//statement[.//fillin and ancestor::exercise/evaluation]",
}
ASSETS = ["ALL"] + list(ASSET_TO_XPATH.keys())

ASSET_TO_DIR = {
    "webwork": ["webwork"],
    "latex-image": ["latex-image"],
    "sageplot": ["sageplot"],
    "asymptote": ["asymptote"],
    "prefigure": ["prefigure"],
    "youtube": ["youtube", "play-button", "qrcode"],
    "interactive": ["preview", "qrcode"],
    "codelens": ["trace"],
    "datafile": ["datafile"],
    "mermaid": ["mermaid"],
    "myopenmath": ["problems"],
    "dynamic-subs": ["dynamic_subs"],
}

ASSET_FORMATS: t.Dict[str, t.Dict[str, t.List[str]]] = {
    "pdf": {
        "asymptote": ["pdf"],
        "latex-image": [],
        "sageplot": ["pdf", "png"],
        "prefigure": ["pdf"],
        "mermaid": ["png"],
    },
    "latex": {
        "asymptote": ["pdf"],
        "latex-image": [],
        "sageplot": ["pdf", "png"],
        "prefigure": ["pdf"],
        "mermaid": ["png"],
    },
    "html": {
        "asymptote": ["html"],
        "latex-image": ["svg"],
        "sageplot": ["html", "svg"],
        "prefigure": ["svg"],
    },
    "runestone": {
        "asymptote": ["html"],
        "latex-image": ["svg"],
        "sageplot": ["html", "svg"],
        "prefigure": ["svg"],
    },
    "epub": {
        "asymptote": ["svg"],
        "latex-image": ["svg"],
        "sageplot": ["svg"],
        "prefigure": ["svg"],
        "mermaid": ["png"],
    },
    "kindle": {
        "asymptote": ["png"],
        "latex-image": ["png"],
        "sageplot": ["png"],
        "prefigure": ["png"],
        "mermaid": ["png"],
    },
    "braille": {
        "asymptote": ["all"],
        "latex-image": ["all"],
        "sageplot": ["all"],
        "mermaid": ["png"],
    },
    "revealjs": {
        "asymptote": ["html"],
        "latex-image": ["svg"],
        "sageplot": ["html", "svg"],
    },
    "webwork": {
        "asymptote": [],
        "latex-image": [],
        "sageplot": [],
        "mermaid": [],
    },
    "custom": {
        "asymptote": ["all"],
        "latex-image": ["all"],
        "sageplot": ["all"],
        "prefigure": ["all"],
        "mermaid": ["png"],
    },
}

PROJECT_RESOURCES = {
    "project.ptx": Path("project.ptx"),
    "codechat_config.yaml": Path("codechat_config.yaml"),
    ".gitignore": Path(".gitignore"),
    ".devcontainer.json": Path(".devcontainer.json"),
    "requirements.txt": Path("requirements.txt"),
    "pretext-cli.yml": Path(".github", "workflows", "pretext-cli.yml"),
}

DEPRECATED_PROJECT_RESOURCES = {
    "deploy.yml": Path(".github", "workflows", "deploy.yml"),
    "test-build.yml": Path(".github", "workflows", "test-build.yml"),
}
