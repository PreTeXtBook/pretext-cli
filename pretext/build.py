from lxml import etree as ET
import logging
import os
import shutil
import sys
import pathlib

from . import static, utils
from .static.pretext import pretext as core

# Get access to logger
log = logging.getLogger('ptxlogger')

def linux_path(path):
    # hack to make core ptx happy
    p = pathlib.Path(path)
    return p.as_posix()

def html(ptxfile,pub_file,output,stringparams):
    utils.ensure_directory(output)
    log.info(f"\nNow building HTML into {output}\n")
    try:
        core.html(ptxfile, linux_path(pub_file), stringparams, output)
        log.info(f"\nSuccess! Run `pretext view html` to see the results.\n")
    except Exception:
        log.debug(f"There was a fatal error here", exc_info=True)
        log.critical(
            f"A fatal error has occurred. For more info, run pretext with `-v debug`")
        sys.exit()



def latex(ptxfile,pub_file,output,stringparams):
    utils.ensure_directory(output)
    log.info(f"\nNow building LaTeX into {output}\n")
    try:
        core.latex(ptxfile, linux_path(pub_file), stringparams, None, output)
        log.info(f"\nSuccess! Run `pretext view latex` to see the results.\n")
    except Exception:
        log.debug(f"There was a fatal error here", exc_info=True)
        log.critical(
            f"A fatal error has occurred. For more info, run pretext with `-v debug`")
        sys.exit()


def pdf(ptxfile,pub_file,output,stringparams):
    utils.ensure_directory(output)
    log.info(f"\nNow building LaTeX into {output}\n")
    try:
        core.pdf(ptxfile, linux_path(pub_file), stringparams,
             None, dest_dir=output)
        log.info(f"\nSuccess! Run `pretext view pdf` to see the results.\n")
    except Exception:
        log.debug(f"There was a fatal error here", exc_info=True)
        log.critical(f"A fatal error has occurred. For more info, run pretext with `-v debug`")
        sys.exit()



# Function to build diagrams/images contained in source.
def diagrams(ptxfile, pub_file, output, params, formats):
    # We assume passed paths are absolute.
    # set images directory
    # parse source so we can check for image types.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//latex-image")) > 0:
        image_output = os.path.abspath(os.path.join(output, 'latex-image'))
        utils.ensure_directory(image_output)
        log.info('Now generating latex-images\n\n')
        # call pretext-core's latex image module:
        core.latex_image_conversion(
            xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params, xmlid_root=None, data_dir=None, dest_dir=image_output, outformat=formats)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//sageplot")) > 0:
        image_output = os.path.abspath(os.path.join(output, 'sageplot'))
        utils.ensure_directory(image_output)
        log.info('Now generating sageplot images\n\n')
        core.sage_conversion(
            xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params, xmlid_root=None, dest_dir=image_output, outformat=formats)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//asymptote")) > 0:
        image_output = os.path.abspath(
            os.path.join(output, 'asymptote'))
        utils.ensure_directory(image_output)
        log.info('Now generating asymptote images\n\n')
        core.asymptote_conversion(
            xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params, xmlid_root=None, dest_dir=image_output, outformat=formats)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//interactive[not(@preview)]"))> 0:
        image_output = os.path.abspath(
                    os.path.join(output, 'preview'))
        utils.ensure_directory(image_output)
        log.info('Now generating preview images for interactives\n\n')
        core.preview_images(
            xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params, xmlid_root=None, dest_dir=image_output)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//video[@youtube]")) > 0:
        image_output = os.path.abspath(
            os.path.join(output, 'youtube'))
        utils.ensure_directory(image_output)
        log.info('Now generating youtube previews\n\n')
        core.youtube_thumbnail(
            xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params, xmlid_root=None, dest_dir=image_output, outformat=formats)


def webwork(ptxfile, pub_file, dest_dir, params, server_params):
    # Assume passed paths are absolute.
    # Set directory for WW representations.
    # dest_dir = os.path.join(dest_dir, outfile)
    utils.ensure_directory(dest_dir)
    # call the webwork-to-xml routine from core
    # the fourth argument seems to be for debugging on the ptx core side
    # the fifth argument has to do with ww server config; here just use
    # the default/recommended config in PreTeXt Guide. But this is passed as one of the collection of stringparams, so set to None here.  Sams for the pub_file.
    core.webwork_to_xml(xml_source=ptxfile, pub_file=None, stringparams=params, abort_early=True, server_params=server_params, dest_dir=dest_dir)

