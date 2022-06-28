# eventually we need to refactor ala
#   https://docs.python.org/3/library/importlib.html#module-importlib.resources
# But for practical purposes the CLI is realized as actual files in the filesystem, so we'll
# assume this for now
#   import importlib.resources as pkg_resources

import os
from pathlib import Path
from lxml import etree as ET
from . import __file__ as STATIC_PATH

def path(*args): #TODO make pathlib.Path
    """
    Returns absolute path to files in the static folder of the distribution.
    """
    return os.path.abspath(os.path.join(
        os.path.dirname(STATIC_PATH),
        *args
    ))

def core_xsl(*args,as_path=False): #TODO deprecate
    xsl_path = path("xsl",*args)
    if as_path:
        return xsl_path
    else:
        return ET.parse(xsl_path)

def core_xsl_dir_path():
    return Path(__file__).parent/'xsl'
