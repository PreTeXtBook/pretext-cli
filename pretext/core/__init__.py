try:
    from .pretext import *
    from . import pretext
except ImportError as e:
    raise ImportError(
        "Failed to import the core pretext.py file. Perhaps the file is unavailable? "
        "Run `scripts/fetch_core.py` to grab a copy of pretex core.\n"
        "The original error message is: " + e.msg
    )
from .. import resources
from .. import CORE_COMMIT, VERSION

set_ptx_path(resources.resource_base_path() / "core")


def cli_build_message() -> str:
    """
    Override the build_info_message function of core to report that the CLI was used to build.
    """
    return (
        f"built with the PreTeXt-CLI, version {VERSION} using core commit {CORE_COMMIT}"
    )


pretext.build_info_message = cli_build_message
