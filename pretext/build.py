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
        core.html(ptxfile, utils.linux_path(pub_file), stringparams, xmlid_root, file_format, custom_xsl, None, output)

def latex(ptxfile,pub_file,output,stringparams,custom_xsl):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory("."):
        core.latex(ptxfile, utils.linux_path(pub_file), stringparams, custom_xsl, None, output)

def pdf(ptxfile,pub_file,output,stringparams,custom_xsl,pdf_method):
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    with utils.working_directory("."):
        core.pdf(ptxfile, utils.linux_path(pub_file), stringparams, custom_xsl,
                 None, dest_dir=output, method=pdf_method)

# Function to build diagrams/images contained in source.
def diagrams(ptxfile, pub_file, output, params, target_format, diagrams_format, xmlid_root, pdf_method):
    # Dictionary of formats for images based on source and target
    formats = {
        'pdf': {'latex-image' : [None], 'sageplot': ['pdf','png'], 'asymptote': ['pdf']},
        'latex':  {'latex-image': [None], 'sageplot': ['pdf','png'], 'asymptote': ['pdf']},
        'html': {'latex-image' : ['svg'], 'sageplot': ['html','svg'], 'asymptote': ['html']}
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
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating latex-images\n\n')
        # call pretext-core's latex image module:
        with utils.working_directory("."):
            for outformat in formats[target_format]['latex-image']:
                core.latex_image_conversion(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    xmlid_root=xmlid_root, dest_dir=image_output, outformat=outformat, method=pdf_method)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//sageplot")) > 0 and formats[target_format]['sageplot'] is not None:
        image_output = os.path.abspath(os.path.join(output, 'sageplot'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating sageplot images\n\n')
        with utils.working_directory("."):
            for outformat in formats[target_format]['sageplot']:
                core.sage_conversion(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    xmlid_root=xmlid_root, dest_dir=image_output, outformat=outformat)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//asymptote")) > 0 and formats[target_format]['asymptote']:
        image_output = os.path.abspath(
            os.path.join(output, 'asymptote'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating asymptote images\n\n')
        with utils.working_directory("."):
            for outformat in formats[target_format]['asymptote']:
                core.asymptote_conversion(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    xmlid_root=xmlid_root, dest_dir=image_output, outformat=outformat, method='server')
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//interactive[not(@preview)]"))> 0:
        image_output = os.path.abspath(
                    os.path.join(output, 'preview'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating preview images for interactives\n\n')
        with utils.working_directory("."):
            core.preview_images(
                xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                xmlid_root=xmlid_root, dest_dir=image_output)
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//video[@youtube]")) > 0:
        image_output = os.path.abspath(
            os.path.join(output, 'youtube'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating youtube previews\n\n')
        with utils.working_directory("."):
            core.youtube_thumbnail(
                xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                xmlid_root=xmlid_root, dest_dir=image_output)


def webwork(ptxfile, pub_file, dest_dir, params, server_params):
    # Assume passed paths are absolute.
    # Set directory for WW representations.
    # dest_dir = os.path.join(dest_dir, outfile)
    os.makedirs(dest_dir, exist_ok=True)
    # call the webwork-to-xml routine from core
    # the fourth argument seems to be for debugging on the ptx core side
    # the fifth argument has to do with ww server config; here just use
    # the default/recommended config in PreTeXt Guide. But this is passed as one of the collection of stringparams, so set to None here.  Sams for the pub_file.
    with utils.working_directory("."):
        core.webwork_to_xml(
            xml_source=ptxfile, pub_file=None, stringparams=params,
            abort_early=True, server_params=server_params, dest_dir=dest_dir)
