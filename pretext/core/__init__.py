try:
    from .pretext import *
except ImportError as e:
    raise ImportError(
        "Failed to import the core pretext.py file. Perhaps the file is unavailable? "
        "Run `scripts/fetch_core.py` to grab a copy of pretex core.\n"
        "The original error message is: " + e.msg
    )
from . import resources

set_ptx_path(resources.path())
