import typing as t
from pathlib import Path

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
        "mermaid",
    ],
    "latex": [
        "webwork",
        "sageplot",
        "asymptote",
        "youtube",
        "codelens",
        "datafile",
        "interactive",
        "mermaid",
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
        "mermaid",
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
    "mermaid": ".//mermaid",
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
    "mermaid": ["mermaid"],
}

ASSET_FORMATS: t.Dict[str, t.Dict[str, t.List[str]]] = {
    "pdf": {
        "asymptote": ["pdf"],
        "latex-image": [],
        "sageplot": ["pdf", "png"],
        "mermaid": ["png"],
    },
    "latex": {
        "asymptote": ["pdf"],
        "latex-image": [],
        "sageplot": ["pdf", "png"],
        "mermaid": ["png"],
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
        "mermaid": ["png"],
    },
    "kindle": {
        "asymptote": ["png"],
        "latex-image": ["png"],
        "sageplot": ["png"],
        "mermaid": ["png"],
    },
    "braille": {
        "asymptote": ["all"],
        "latex-image": ["all"],
        "sageplot": ["all"],
        "mermaid": ["png"],
    },
    "custom": {
        "asymptote": ["all"],
        "latex-image": ["all"],
        "sageplot": ["all"],
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
