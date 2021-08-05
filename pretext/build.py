from re import T
from lxml import etree as ET
import logging
import os
import sys
import pathlib

from . import utils
from .static.pretext import pretext as core

# Get access to logger
log = logging.getLogger('ptxlogger')

def linux_path(path):
    # hack to make core ptx happy
    p = pathlib.Path(path)
    return p.as_posix()

def html(ptxfile,pub_file,output,stringparams,custom_xsl):
    utils.ensure_directory(output)
    log.info(f"\nNow building HTML into {output}\n")
    with utils.working_directory("."):
        core.html(ptxfile, linux_path(pub_file), stringparams, custom_xsl, output)

def latex(ptxfile,pub_file,output,stringparams,custom_xsl):
    utils.ensure_directory(output)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory("."):
        core.latex(ptxfile, linux_path(pub_file), stringparams, custom_xsl, None, output)

def pdf(ptxfile,pub_file,output,stringparams,custom_xsl):
    utils.ensure_directory(output)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory("."):
        core.pdf(ptxfile, linux_path(pub_file), stringparams, custom_xsl,
                 None, dest_dir=output)

# Function to build diagrams/images contained in source.
def diagrams(ptxfile, pub_file, output, params, target_format, diagrams_format):
    # Dictionary of formats for images based on source and target
    formats = {
        'pdf': {'latex-image' : None, 'sageplot': 'pdf', 'asymptote': 'pdf'},
        'latex':  {'latex-image': None, 'sageplot': 'pdf', 'asymptote': 'pdf'},
        'html': {'latex-image' : 'svg', 'sageplot': 'svg', 'asymptote': 'html'}
               }
    # set format to all when appropriate
    if diagrams_format == 'all':
        formats[target_format] = {key: 'all' for key in formats[target_format]}
    # We assume passed paths are absolute.
    # set images directory
    # parse source so we can check for image types.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()

    if len(source_xml.xpath("/pretext/*[not(docinfo)]//latex-image")) > 0 and formats[target_format]['latex-image'] is not None:
        image_output = os.path.abspath(os.path.join(output, 'latex-image'))
        utils.ensure_directory(image_output)
        log.info('Now generating latex-images\n\n')
        # call pretext-core's latex image module:
        with utils.working_directory("."):
            core.latex_image_conversion(
                xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params,
                xmlid_root=None, dest_dir=image_output, outformat=formats[target_format]['latex-image'])
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//sageplot")) > 0 and formats[target_format]['sageplot'] is not None:
        image_output = os.path.abspath(os.path.join(output, 'sageplot'))
        utils.ensure_directory(image_output)
        log.info('Now generating sageplot images\n\n')
        with utils.working_directory("."):
            core.sage_conversion(
                xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params,
                xmlid_root=None, dest_dir=image_output, outformat=formats[target_format]['sageplot'])
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//asymptote")) > 0 and formats[target_format]['asymptote']:
        image_output = os.path.abspath(
            os.path.join(output, 'asymptote'))
        utils.ensure_directory(image_output)
        log.info('Now generating asymptote images\n\n')
        with utils.working_directory("."):
            core.asymptote_conversion(
                xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params,
                xmlid_root=None, dest_dir=image_output, outformat=formats[target_format]['asymptote'], method='server')
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//interactive[not(@preview)]"))> 0:
        image_output = os.path.abspath(
                    os.path.join(output, 'preview'))
        utils.ensure_directory(image_output)
        log.info('Now generating preview images for interactives\n\n')
        with utils.working_directory("."):
            core.preview_images(
                xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params,
                xmlid_root=None, dest_dir=image_output)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//video[@youtube]")) > 0:
        image_output = os.path.abspath(
            os.path.join(output, 'youtube'))
        utils.ensure_directory(image_output)
        log.info('Now generating youtube previews\n\n')
        with utils.working_directory("."):
            core.youtube_thumbnail(
                xml_source=ptxfile, pub_file=linux_path(pub_file), stringparams=params,
                xmlid_root=None, dest_dir=image_output)


def webwork(ptxfile, pub_file, dest_dir, params, server_params):
    # Assume passed paths are absolute.
    # Set directory for WW representations.
    # dest_dir = os.path.join(dest_dir, outfile)
    utils.ensure_directory(dest_dir)
    # call the webwork-to-xml routine from core
    # the fourth argument seems to be for debugging on the ptx core side
    # the fifth argument has to do with ww server config; here just use
    # the default/recommended config in PreTeXt Guide. But this is passed as one of the collection of stringparams, so set to None here.  Sams for the pub_file.
    with utils.working_directory("."):
        core.webwork_to_xml(
            xml_source=ptxfile, pub_file=None, stringparams=params,
            abort_early=True, server_params=server_params, dest_dir=dest_dir)
