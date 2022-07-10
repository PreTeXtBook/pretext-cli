# eventually we need to refactor ala
#   https://docs.python.org/3/library/importlib.html#module-importlib.resources
# But for practical purposes the CLI is realized as actual files in the filesystem, so we'll
# assume this for now
#   import importlib.resources as pkg_resources

import os
from pathlib import Path
from lxml import etree as ET
import zipfile
from . import __file__ as STATIC_PATH
from .. import utils
from .. import CORE_COMMIT

def path(*args) -> Path:
    # Checks that the local static path ~/.ptx/ contains the static files needed for core, and installs them if they are missing (or if the version is different from the installed version of pretext).  Then returns the absolute path to the static files (appending arguments)
    local_base_path = Path.home()/'.ptx'
    local_commit_file = Path(local_base_path)/".commit"
    if not Path.is_file(local_commit_file):
        print("Static pretext files do not appear to be installed.  Installing now.")
        install_static(local_base_path)
    # check that the static core_commit matches current core_commit
    with open(local_commit_file, "r") as f:
        static_commit = f.readline()
    if static_commit != CORE_COMMIT:
        print("Static pretext files are out of date.  Installing them now.")
        install_static(local_base_path)
    return local_base_path.joinpath(*args)

def install_static(local_base_path):
    static_zip = (Path(STATIC_PATH).parent).joinpath("static.zip")
    with zipfile.ZipFile(static_zip,"r") as zip:
        zip.extractall(local_base_path)
    # Write the current commit to local file
    with open(local_base_path/".commit","w") as f:
        f.write(CORE_COMMIT)
    print(f"Static files required for pretext have now been installed to {local_base_path}")
    return

def templates_path(*args): #TODO make pathlib.Path
    """
    Returns absolute path to files in the static folder of the distribution.
    """
    return (Path(STATIC_PATH).parent).joinpath("templates",
        *args)

def core_xsl(*args,as_path=False): #TODO deprecate
    xsl_path = path("xsl",*args)
    if as_path:
        return xsl_path
    else:
        return ET.parse(xsl_path)

def core_xsl_dir_path():
    return Path(__file__).parent/'xsl'
