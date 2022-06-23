from re import T
from lxml import etree as ET
import logging
import os
from pathlib import Path
import sys
from typing import Optional

from . import utils, core

# Get access to logger
log = logging.getLogger('ptxlogger')

def html(ptxfile:Path,pub_file:Path,output:Path,stringparams,custom_xsl:Optional[Path],xmlid_root,zipped=False):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building HTML into {output}\n")
    if xmlid_root is not None:
        log.info(f"Only building @xml:id `{xmlid_root}`\n")
    if zipped:
        file_format = 'zip'
    else:
        file_format = 'html'
    with utils.working_directory(Path()): # ensure working directory is preserved
        try:
            core.html(
                ptxfile.as_posix(),
                pub_file.as_posix(),
                stringparams,
                xmlid_root,
                file_format,
                custom_xsl and custom_xsl.as_posix(), # pass None or posix string
                None,
                output.as_posix()
            )
        except Exception as e:
            log.critical(e)
            log.debug(f"Critical error info:\n****\n", exc_info=True)
            sys.exit('Failed to build html.  Exiting...')

def latex(ptxfile:Path,pub_file:Path,output:Path,stringparams,custom_xsl:Optional[Path]):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory(Path()): # ensure working directory is preserved
        try:
            core.latex(
                ptxfile.as_posix(), 
                pub_file.as_posix(), 
                stringparams, 
                custom_xsl and custom_xsl.as_posix(), # pass None or posix string
                None, 
                output.as_posix()
            )
        except Exception as e:
            log.critical(e)
            log.debug(f"Critical error info:\n****\n", exc_info=True)
            sys.exit('Failed to build latex.  Exiting...')

def pdf(ptxfile:Path,pub_file:Path,output:Path,stringparams,custom_xsl:Optional[Path],pdf_method:str):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory(Path()): # ensure working directory is preserved
        try:
            core.pdf(
                ptxfile.as_posix(), 
                pub_file.as_posix(), 
                stringparams, 
                custom_xsl and custom_xsl.as_posix(), # pass None or posix string
                None, 
                dest_dir=output.as_posix(), 
                method=pdf_method
            )
        except Exception as e:
            log.critical(e)
            log.debug(f"Critical error info:\n****\n", exc_info=True)
            sys.exit('Failed to build pdf.  Exiting...')
