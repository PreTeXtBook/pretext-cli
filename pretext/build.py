from re import T
from lxml import etree as ET
import logging
import os

from . import utils
from .static.pretext import pretext as core

# Get access to logger
log = logging.getLogger('ptxlogger')

def html(ptxfile,pub_file,output,stringparams,custom_xsl,xmlid_root,zipped=False):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building HTML into {output}\n")
    if xmlid_root is not None:
        log.info(f"Only building @xml:id `{xmlid_root}`\n")
    if zipped:
        file_format = 'zip'
    else:
        file_format = 'html'
    with utils.working_directory("."):
        try:
            core.html(ptxfile, utils.linux_path(pub_file), stringparams, xmlid_root, file_format, custom_xsl, None, output)
        except Exception as e:
            log.critical(e)
            log.debug(f"Critical error info:\n****\n", exc_info=True)

def latex(ptxfile,pub_file,output,stringparams,custom_xsl):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory("."):
        try:
            core.latex(ptxfile, utils.linux_path(pub_file), stringparams, custom_xsl, None, output)
        except Exception as e:
            log.critical(e)
            log.debug(f"Critical error info:\n****\n", exc_info=True)

def pdf(ptxfile,pub_file,output,stringparams,custom_xsl,pdf_method):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory("."):
        try:
            core.pdf(ptxfile, utils.linux_path(pub_file), stringparams, custom_xsl,
                 None, dest_dir=output, method=pdf_method)
        except Exception as e:
            log.critical(e)
            log.debug(f"Critical error info:\n****\n", exc_info=True)
