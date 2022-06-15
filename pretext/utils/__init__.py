import os
from contextlib import contextmanager
import pathlib
import logging

from .. import static
from .server import *
from .xml import *

# Get access to logger
log = logging.getLogger('ptxlogger')

@contextmanager
def working_directory(path):
    """
    Temporarily change the current working directory.

    Usage:
    with working_directory(path):
        do_things()   # working in the given path
    do_other_things() # back to original path
    """
    current_directory=os.getcwd()
    os.chdir(path)
    log.debug(f"Now working in directory {path}")
    try:
        yield
    finally:
        os.chdir(current_directory)
        log.debug(f"Successfully changed directory back to {current_directory}")

def linux_path(path):
    # hack to make core ptx and xsl:import happy
    p = pathlib.Path(path)
    return p.as_posix()


def directory_exists(path):
    """
    Checks if the directory exists.
    """
    return os.path.exists(path)


def requirements_version(dirpath=os.getcwd()):
    try:
        with open(os.path.join(project_path(dirpath),'requirements.txt'),'r') as f:
            for line in f.readlines():
                if 'pretextbook' in line:
                    return line.split("==")[1].strip()
    except Exception as e:
        log.debug("Could not read `requirements.txt`:")
        log.debug(e)
        return None
