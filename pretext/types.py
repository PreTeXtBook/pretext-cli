import typing as t

# List of valid formats for a target.
# TODO: sync with constants.BUILD_FORMATS
Format = t.Literal[
    "html",
    "latex",
    "pdf",
    "epub",
    "kindle",
    "braille",
    "webwork",
    "custom",
]

# List of valid latex engines for a target.
LatexEngine = t.Literal["xelatex", "latex", "pdflatex"]

BrailleMode = t.Literal["emboss", "electronic"]

Compression = t.Literal["zip"]

AssetTable = t.Dict[str, t.Dict[str, bytes]]
