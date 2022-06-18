from lxml import etree as ET
import os
import logging
from . import utils
from .static.pretext import pretext as core

# Get access to logger
log = logging.getLogger('ptxlogger')

# generate latex-image assets
def latex_image(ptxfile, pub_file, output, params, target_format, xmlid_root, pdf_method, all_formats=False):
    # Dictionary of formats for images based on target
    formats = {
        'pdf': None,
        'latex':  None,
        'html': ['svg'],
    }
    # set overwrite formats to all when appropriate
    if all_formats:
        formats[target_format] = {key: ['all'] for key in formats[target_format]}
    # We assume passed paths are absolute.
    # set images directory
    # parse source so we can check for latex-image.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//latex-image")) > 0 and formats[target_format] is not None:
        image_output = os.path.abspath(os.path.join(output, 'latex-image'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating latex-images\n\n')
        # Check for external requirements
        utils.check_asset_execs('latex-image', formats[target_format])
        # call pretext-core's latex image module:
        with utils.working_directory("."):
            for outformat in formats[target_format]:
                try:
                    core.latex_image_conversion(
                        xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                        xmlid_root=xmlid_root, dest_dir=image_output, outformat=outformat, method=pdf_method)
                except Exception as e:
                    log.critical(e)
                    log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No latex-image elements found.")

# generate sageplot assets
def sageplot(ptxfile, pub_file, output, params, target_format, xmlid_root, all_formats=False):
    # Dictionary of formats for images based on target
    formats = {
        'pdf': ['pdf','png'],
        'latex':  ['pdf','png'],
        'html': ['html','svg'],
    }
    # set overwrite formats to all when appropriate
    if all_formats:
        formats[target_format] = {key: ['all'] for key in formats[target_format]}
    # We assume passed paths are absolute.
    # set images directory
    # parse source so we can check for sageplot.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//sageplot")) > 0 and formats[target_format] is not None:
        image_output = os.path.abspath(os.path.join(output, 'sageplot'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating sageplot images\n\n')
        # Check for external requirements
        utils.check_asset_execs('sageplot', formats[target_format])
        with utils.working_directory("."):
            try:
                for outformat in formats[target_format]:
                    core.sage_conversion(
                        xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                        xmlid_root=xmlid_root, dest_dir=image_output, outformat=outformat)
            except Exception as e:
                log.critical(e)
                log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No sageplot elements found.")

# generate asymptote assets
def asymptote(ptxfile, pub_file, output, params, target_format, xmlid_root, all_formats=False):
    # Dictionary of formats for images based on target
    formats = {
        'pdf': ['pdf'],
        'latex':  ['pdf'],
        'html': ['html'],
    }
    # set overwrite formats to all when appropriate
    if all_formats:
        formats[target_format] = {key: ['all'] for key in formats[target_format]}
    # We assume passed paths are absolute.
    # parse source so we can check for asymptote.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//asymptote")) > 0 and formats[target_format] is not None:
        image_output = os.path.abspath(
            os.path.join(output, 'asymptote'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating asymptote images\n\n')
        with utils.working_directory("."):
            try:
                for outformat in formats[target_format]:
                    core.asymptote_conversion(
                        xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                        xmlid_root=xmlid_root, dest_dir=image_output, outformat=outformat, method='server')
            except Exception as e:
                log.critical(e)
                log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No asymptote elements found.")

# generate interactive preview assets
def interactive(ptxfile, pub_file, output, params, xmlid_root):
    # We assume passed paths are absolute.
    # parse source so we can check for interactives.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//interactive")) > 0:
        image_output = os.path.abspath(
                    os.path.join(output, 'preview'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating preview images for interactives\n\n')
        # Check for external requirements
        utils.check_asset_execs('interactive', formats[target_format])
        with utils.working_directory("."):
            try:
                core.preview_images(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    xmlid_root=xmlid_root, dest_dir=image_output)
            except Exception as e:
                log.critical(e)
                log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No interactive elements found.")

# generate youtube thumbnail assets
def youtube(ptxfile, pub_file, output, params, xmlid_root):
    # We assume passed paths are absolute.
    # parse source so we can check for videos.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("/pretext/*[not(docinfo)]//video[@youtube]")) > 0:
        image_output = os.path.abspath(
            os.path.join(output, 'youtube'))
        os.makedirs(image_output, exist_ok=True)
        log.info('Now generating youtube previews\n\n')
        with utils.working_directory("."):
            try:
                core.youtube_thumbnail(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    xmlid_root=xmlid_root, dest_dir=image_output)
            except Exception as e:
                log.critical(e)
                log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No video@youtube elements found.")

# generate webwork assets
def webwork(ptxfile, pub_file, output, params):
    # We assume passed paths are absolute.
    # parse source so we can check for webwork.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath('//webwork[node()|@*]')) > 0:
        ww_output = os.path.abspath(
            os.path.join(output, 'webwork'))
        os.makedirs(ww_output, exist_ok=True)
        log.info('Now generating webwork representation\n\n')
        with utils.working_directory("."):
            try:
                core.webwork_to_xml(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    abort_early=True, dest_dir=ww_output, server_params=None)
            except Exception as e:
                log.critical(e)
                log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No webwork elements found.")

# generate codelens trace assets
def codelens(ptxfile, pub_file, output, params, xmlid_root):
    # We assume passed paths are absolute.
    # parse source so we can check for webwork.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if len(source_xml.xpath("//program[@interactive = 'codelens']")) > 0:
        trace_output = os.path.abspath(
            os.path.join(output, 'trace'))
        os.makedirs(trace_output, exist_ok=True)
        log.info('Now generating codelens trace\n\n')
        with utils.working_directory("."):
            try:
                core.tracer(
                    xml_source=ptxfile, pub_file=utils.linux_path(pub_file), stringparams=params,
                    xmlid_root=xmlid_root, dest_dir=trace_output,)
            except Exception as e:
                log.critical(e)
                log.debug(f"Critical error info:\n****\n", exc_info=True)
    else:
        log.info("Note: No program elements using codelens found.")
