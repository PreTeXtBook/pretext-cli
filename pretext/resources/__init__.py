import importlib.resources
import logging
from pathlib import Path
import shutil
import zipfile

from .. import VERSION, CORE_COMMIT

log = logging.getLogger("ptxlogger")

_RESOURCE_BASE_PATH = Path.home() / ".ptx" / VERSION


def install(reinstall: bool = False) -> None:
    if _RESOURCE_BASE_PATH.exists():
        if reinstall:
            log.info(f"Deleting existing resources at {_RESOURCE_BASE_PATH}")
            shutil.rmtree(_RESOURCE_BASE_PATH)
        else:
            log.warning(f"Resources are already installed at {_RESOURCE_BASE_PATH}")
            return
    _RESOURCE_BASE_PATH.mkdir(parents=True)

    log.info("Installing core resources")
    with importlib.resources.path("pretext.resources", "core.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=_RESOURCE_BASE_PATH)
        (_RESOURCE_BASE_PATH / f"pretext-{CORE_COMMIT}").rename(
            _RESOURCE_BASE_PATH / "core"
        )

    log.info("Installing templates")
    (_RESOURCE_BASE_PATH / "templates").mkdir()
    with importlib.resources.path("pretext.resources", "templates.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=_RESOURCE_BASE_PATH / "templates")

    log.info("Installing pelican files")
    (_RESOURCE_BASE_PATH / "pelican").mkdir()
    with importlib.resources.path("pretext.resources", "pelican.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=_RESOURCE_BASE_PATH / "pelican")


def resource_base_path() -> Path:
    if not _RESOURCE_BASE_PATH.exists():
        log.info(f"Installing resources to {_RESOURCE_BASE_PATH}")
        install()
    return _RESOURCE_BASE_PATH
