import os
from contextlib import contextmanager
import pathlib
import logging
import platform

from ..static.pretext import pretext as core
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

def check_executable(exec_name):
    try:
        exec_cmd = core.get_executable_cmd(exec_name)[0]
        log.debug(f"PTX-CLI: Executable command {exec_name} found at {exec_cmd}")
        return exec_cmd
    except OSError as e:
        log.debug(e)

def check_asset_execs(element, outformats):
    # outformats is assumed to be a list of formats.
    # Note that asymptote is done via server, so doesn't require asy.  We could check for an internet connection here for that and webwork, etc.
    log.debug(f"trying to check assets for {element} and output format {outformats}")
    # Create list of executables needed based on output format
    required_execs = []
    if element == "latex-image":
        required_execs = ['xelatex']
        if 'svg' in outformats or 'all' in outformats:
            required_execs.append('pdfsvg')
        if 'png' in outformats or 'all' in outformats:
            required_execs.append('pdfpng')
        if 'eps' in outformats or 'all' in outformats:
            required_execs.append('pdfeps')
    if element == "sageplot":
        required_execs = ['sage']
    if element == "interactive":
        required_execs = ['pageres']
    install_hints = {
        'xelatex':{
            'Windows': 'See https://pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''},
        'pdfsvg': {
            'Windows': 'Follow the instructions at https://pretextbook.org/doc/guide/html/section-installing-pdf2svg.html to install pdf2svg',
            'Darwin': '',
            'Linux': 'You should be able to install pdf2svg with your package manager (e.g., `sudo apt install pdf2svg`.  See https://github.com/dawbarton/pdf2svg#pdf2svg.'},
        'pdfpng': {
            'Windows': 'See https:// pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''},
        'pdfeps': {
            'Windows': 'See https:// pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''},
        'sage': {
            'Windows': 'See https://doc.sagemath.org/html/en/installation/index.html#windows',
            'Darwin': 'https://doc.sagemath.org/html/en/installation/index.html#macos',
            'Linux': 'See https://doc.sagemath.org/html/en/installation/index.html#linux'},
        'pageres': {
            'Windows': 'See https:// pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''}
        }
    for required_exec in required_execs:
        if check_executable(required_exec) is None:
            log.warning(f"In order to generate {element} into formats {outformats}, you must have {required_exec} installed, but this appears to be missing or configured incorrectly in pretext.ptx")
            #print installation hints based on operating system and missing program.
            log.info(install_hints[required_exec][platform.system()])
    
