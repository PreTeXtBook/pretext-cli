from lxml import etree as ET

from . import static, document, utils


def html(ptxfile,output,stringparams):
    import os, shutil
    # from pathlib import Path
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = os.path.join(static.filepath('xsl'), 'pretext-html.xsl')
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
    import os
    import shutil
    # import sys
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = os.path.join(static.filepath('xsl'), 'pretext-latex.xsl')
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
def diagrams(ptxfile, output, params):
    import os
    from .static.pretext import pretext as ptxcore
    # Pass verbosity level to ptxcore sripts:
    ptxcore.set_verbosity(utils._verbosity)
    # We assume passed paths are absolute.
    # set images directory
    image_output = os.path.join(output, 'images')
    utils.ensure_directory(image_output)
    # call pretext-core's latex image module:
    ptxcore.latex_image_conversion(
        xml_source=ptxfile, stringparams=params, xmlid_root=None, data_dir=None, dest_dir=image_output, outformat="svg")



# This start of a utility function to replicate the tasks for xsltproc.
def xsltproc(xslfile, xmlfile, outfile=None, outdir=".", stringparams={}):
    dom = ET.parse(xmlfile)

    utils._verbose('XSL conversion of {} by {}'.format(xmlfile, xslfile))
    debug_string = 'XSL conversion via {} of {} to {} and/or into directory {} with parameters {}'
    utils._debug(debug_string.format(xslfile, xmlfile, outfile, outdir, stringparams))
    # string parameters arrive in a "plain" string:string dictionary
    # but the values need to be prepped for lxml use, always
    stringparams = {key: ET.XSLT.strparam(value) for (
        key, value) in stringparams.items()}
    # xinclude:
    try:
        dom.xinclude()
    except:
        print('there was an error with xinclude')
    xslt = ET.parse(xslfile)
    utils._verbose('Loading the transform')
    transform = ET.XSLT(xslt)
    utils._verbose('Transforming the source')
    with utils.working_directory(outdir):
        newdom = transform(dom, **stringparams)
        #grab the format from xslfile and use it to name logfile:
        logfile = xslfile[xslfile.find('pretext-'):].replace('pretext-','').replace('.xsl','')+'-build.log'
        with open(logfile,"w") as log:
            log.write(str(transform.error_log))
        # also print error_log to console.
        print(transform.error_log)
        # Write output if not done by exsl:document:
        if outfile:
            utils._verbose('Writing output to file specified')
            with open(outfile, "w") as fh:
                fh.write(str(newdom))
