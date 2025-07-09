import importlib.resources
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

from .. import VERSION, CORE_COMMIT

log = logging.getLogger("ptxlogger")

_RESOURCE_BASE_PATH = Path.home() / ".ptx" / VERSION


def install(reinstall: bool = False, npm_install: bool = False) -> None:
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
    shutil.copy2(
        _RESOURCE_BASE_PATH / "templates" / "standalone-project.ptx",
        _RESOURCE_BASE_PATH / "project.ptx",
    )
    shutil.copy2(
        _RESOURCE_BASE_PATH / "templates" / "standalone-publication.ptx",
        _RESOURCE_BASE_PATH / "publication.ptx",
    )

    log.info("Installing rs_cache files")
    (_RESOURCE_BASE_PATH / "rs_cache").mkdir()
    with importlib.resources.path("pretext.resources", "rs_cache.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=_RESOURCE_BASE_PATH / "rs_cache")

    log.info("Installing pelican files")
    (_RESOURCE_BASE_PATH / "pelican").mkdir()
    with importlib.resources.path("pretext.resources", "pelican.zip") as static_zip:
        with zipfile.ZipFile(static_zip, "r") as zip:
            zip.extractall(path=_RESOURCE_BASE_PATH / "pelican")

    if npm_install:
        log.info("Installing npm packages")
        # Look for node_modules and install if we can.  This is a simplified version of the more robust utils.css_node_modules_install, which we cannot use here due to circular imports.
        os.chdir(_RESOURCE_BASE_PATH / "core" / "script" / "cssbuilder")
        try:
            npm_cmd = shutil.which("npm")
            if npm_cmd is None:
                log.warning(
                    "Cannot find npm.  Will try to use prebuilt CSS files instead."
                )
                raise FileNotFoundError
            subprocess.run([npm_cmd, "install", "--engine-strict=true"])
        except Exception as e:
            log.warning(f"Unable to install npm packages for theme building: {e}")
            log.debug(e, exc_info=True)
            return
        # Dynamic substitution script requires node versions > 22.10
        os.chdir(_RESOURCE_BASE_PATH / "core" / "script" / "dynsub")
        try:
            npm_cmd = shutil.which("npm")
            if npm_cmd is None:
                log.warning(
                    "Cannot find npm. Will not be able to extract dynamic substitutions."
                )
                raise FileNotFoundError
            subprocess.run([npm_cmd, "install"])
        except Exception as e:
            log.warning(
                f"Unable to install npm packages for dynamic substitutions: {e}"
            )
            log.debug(e, exc_info=True)
            return


def resource_base_path() -> Path:
    if not _RESOURCE_BASE_PATH.exists():
        log.info(f"Installing resources to {_RESOURCE_BASE_PATH}")
        install()
    return _RESOURCE_BASE_PATH


def get_resource_hash_table() -> dict:
    with importlib.resources.path(
        "pretext.resources", "resource_hash_table.json"
    ) as hash_table:
        return json.load(hash_table.open())
