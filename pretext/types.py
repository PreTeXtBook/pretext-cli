import typing as t

# List of valid formats for a target.
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

AssetTable = t.Dict[str, t.Dict[str, bytes]]
