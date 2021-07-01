from lxml import etree as ET
import logging
import os
import shutil
from . import static, utils
from .static.pretext import pretext as core

# Get access to logger
log = logging.getLogger('ptxlogger')

def html(ptxfile,output,stringparams):
    # from pathlib import Path
    # ptxfile = os.path.abspath('source/main.ptx')
    # xslfile = os.path.join(static.filepath('xsl'), 'pretext-html.xsl')
    static_dir = os.path.dirname(static.__file__)
    xslfile = os.path.join(static_dir, 'xsl', 'pretext-html.xsl')
    # create output directories and move there.
    # output = os.path.abspath(output)
    utils.ensure_directory(output)
    utils.ensure_directory(os.path.join(output,'knowl'))
    utils.ensure_directory(os.path.join(output,'images'))
    # Copy images from source/images
    src = os.path.join(os.path.dirname(os.path.abspath(ptxfile)), 'images')
    if os.path.exists(src):
        src_files = os.listdir(src)
        for file_name in src_files:
            full_file_name = os.path.join(src, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, os.path.join(output, 'images'))
    # transform ptx using xsl:
    xsltproc(xslfile, ptxfile, outfile=None, outdir=output, stringparams=stringparams)


def latex(ptxfile,output,stringparams):
    # ptxfile = os.path.abspath('source/main.ptx')
    # xslfile = os.path.join(static.filepath('xsl'), 'pretext-latex.xsl')
    static_dir = os.path.dirname(static.__file__)
    xslfile = os.path.join(static_dir, 'xsl', 'pretext-latex.xsl')
    #create output directory
    # output = os.path.abspath(output)
    utils.ensure_directory(output)
    utils.ensure_directory(os.path.join(output, 'images'))
    # Copy images from source/images
    # This is less than ideal.  The author is able to provide a path to the static images, but this assumes they are always src="images/foo.png"
    src = os.path.join(os.path.dirname(ptxfile), 'images')
    if os.path.exists(src):
        src_files = os.listdir(src)
        for file_name in src_files:
            full_file_name = os.path.join(src, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, os.path.join(output, 'images'))
    # Do the xsltproc equivalent:
    # params = {"latex.font.size": "'20pt'"}
    xsltproc(xslfile, ptxfile, outfile='main.tex', outdir=output, stringparams=stringparams)


# Function to build diagrams/images contained in source.
def diagrams(ptxfile, output, params, formats):
    # We assume passed paths are absolute.
    # set images directory
    image_output = os.path.join(output, 'images')
    utils.ensure_directory(image_output)
    # parse source so we can check for image types.
    source_xml = ET.parse(ptxfile)
    source_xml.xinclude()
    if source_xml.find("/pretext/*[not(docinfo)]//latex-image") is not None:
        log.info('Now generating latex-images\n\n')
        # call pretext-core's latex image module:
        # NOTE: we set pub_file=NONE since our pubfile has already been added to the params dictionary.
        core.latex_image_conversion(
            xml_source=ptxfile, pub_file=None, stringparams=params, xmlid_root=None, data_dir=None, dest_dir=image_output, outformat=formats)
    if source_xml.find("/pretext/*[not(docinfo)]//sageplot") is not None:
        log.info('Now generating sageplot images\n\n')
        core.sage_conversion(
            xml_source=ptxfile, pub_file=None, stringparams=params, xmlid_root=None, dest_dir=image_output, outformat=formats)
    if source_xml.find("/pretext/*[not(docinfo)]//asymptote") is not None:
        log.info('Now generating asymptote images\n\n')
        core.asymptote_conversion(
            xml_source=ptxfile, pub_file=None, stringparams=params, xmlid_root=None, dest_dir=image_output, outformat=formats)
    if source_xml.find("/pretext/*[not(docinfo)]//interactive[not(@preview)]") is not None:
        log.info('Now generating preview images for interactives\n\n')
        core.preview_images(
            xml_source=ptxfile, pub_file=None, stringparams=params, xmlid_root=None, dest_dir=image_output)
    if source_xml.find("/pretext/*[not(docinfo)]//video[@youtube]") is not None:
        log.info('Now generating youtube previews\n\n')
        core.youtube_thumbnail(
            xml_source=ptxfile, pub_file=None, stringparams=params, xmlid_root=None, dest_dir=image_output, outformat=formats)


def webwork(ptxfile, dest_dir, params, server_params):
    # Assume passed paths are absolute.
    # Set directory for WW representations.
    # dest_dir = os.path.join(dest_dir, outfile)
    utils.ensure_directory(dest_dir)
    # call the webwork-to-xml routine from core
    # the fourth argument seems to be for debugging on the ptx core side
    # the fifth argument has to do with ww server config; here just use
    # the default/recommended config in PreTeXt Guide. But this is passed as one of the collection of stringparams, so set to None here.  Sams for the pub_file.
    core.webwork_to_xml(xml_source=ptxfile, pub_file=None, stringparams=params, abort_early=True, server_params=server_params, dest_dir=dest_dir)

# This start of a utility function to replicate the tasks for xsltproc.
def xsltproc(xslfile, xmlfile, outfile=None, outdir=".", stringparams={}):
    dom = ET.parse(xmlfile)

    log.info('XSL conversion of {} by {}'.format(xmlfile, xslfile))
    debug_string = 'XSL conversion via {} of {} to {} and/or into directory {} with parameters {}'
    log.debug(debug_string.format(xslfile, xmlfile, outfile, outdir, stringparams))

    # string parameters arrive in a "plain" string:string dictionary
    # but the values need to be prepped for lxml use, always
    stringparams = {key: ET.XSLT.strparam(value) for (
        key, value) in stringparams.items()}
    # xinclude:
    dom.xinclude()

    xslt = ET.parse(xslfile)
    log.info('Loading the transform')
    transform = ET.XSLT(xslt)
    log.info('Transforming the source')
    with utils.working_directory(outdir):
        newdom = transform(dom, **stringparams)
        #grab the format from xslfile and use it to name logfile:
        # logfile = xslfile[xslfile.find('pretext-'):].replace('pretext-','').replace('.xsl','')+'-build.log'
        # report any errors
        messages = transform.error_log
        if messages:
            logfile = "build.log"
            with open(logfile,"w") as logout:
                logout.write(str('Messages from application of {}:'.format(xslfile))+'\n')
                log.info('Messages from application of {}:'.format(xslfile))
                for m in messages:
                    logout.write(m.message + '\n')
                    print(m.message)
        # Write output if not done by exsl:document:
        if outfile:
            log.info('Writing output to file specified')
            with open(outfile, "w", encoding='utf-8') as fh:
                fh.write(str(newdom))

