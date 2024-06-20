import importlib.resources
import logging
from pathlib import Path
import shutil
import zipfile

from .. import VERSION, CORE_COMMIT

log = logging.getLogger("ptxlogger")

RESOURCE_BASE_PATH = Path.home() / ".ptx" / VERSION


def install(reinstall: bool = False) -> None:
    if RESOURCE_BASE_PATH.exists():
        if reinstall:
            log.info(f"Deleting existing resources at {RESOURCE_BASE_PATH}")
            shutil.rmtree(RESOURCE_BASE_PATH)
        else:
            log.warning(f"Resources are already installed at {RESOURCE_BASE_PATH}")
            return
    RESOURCE_BASE_PATH.mkdir(parents=True)

    log.info("Installing core resources")
    with importlib.resources.path("pretext.resources", "core.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=RESOURCE_BASE_PATH)
        (RESOURCE_BASE_PATH / f"pretext-{CORE_COMMIT}").rename(
            RESOURCE_BASE_PATH / "core"
        )

    log.info("Installing templates")
    with importlib.resources.path("pretext.resources", "templates.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=RESOURCE_BASE_PATH)
        (RESOURCE_BASE_PATH / f"pretext-{CORE_COMMIT}").rename(
            RESOURCE_BASE_PATH / "core"
        )
