from lxml import etree as ET

from . import static, document, utils


def html(ptxfile,output,stringparams):
    import os, shutil
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
    import os
    import shutil
    # import sys
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
def diagrams(ptxfile, output, params):
    import os
    # We assume passed paths are absolute.
    # set images directory
    image_output = os.path.join(output, 'images')
    utils.ensure_directory(image_output)

    # call pretext-core's latex image module:
    # NOTE: we set pub_file=NONE since our pubfile has already been added to the params dictionary.
    core_latex_image_conversion(
        xml_source=ptxfile, pub_file=None, stringparams=params, xmlid_root=None, data_dir=None,
        dest_dir=image_output, outformat="svg")

# very gross port of core function
def core_latex_image_conversion(xml_source, pub_file, stringparams, xmlid_root, data_dir, dest_dir, outformat):
    # stringparams is a dictionary, best for lxml parsing
    import platform # system, machine()
    import os.path # join()
    import subprocess # call() is Python 3.5
    import os, shutil

    # for killing output
    devnull = open(os.devnull, 'w')
    import tempfile
    tmp_dir = tempfile.mkdtemp()
    # NB: next command uses relative paths, so no chdir(), etc beforehand
    if data_dir:
        copy_data_directory(xml_source, data_dir, tmp_dir)
    ptx_xsl_dir = os.path.join(os.path.dirname(static.__file__),"xsl")
    # support publisher file, subtree argument
    if pub_file:
        stringparams['publisher'] = pub_file
    if xmlid_root:
        stringparams['subtree'] = xmlid_root
    extraction_xslt = os.path.join(ptx_xsl_dir, 'extract-latex-image.xsl')
    # no output (argument 3), stylesheet writes out per-image file
    xsltproc(extraction_xslt, xml_source, None, tmp_dir, stringparams)
    # now work in temporary directory
    with utils.working_directory(tmp_dir):
        # files *only*, from top-level
        files = list(filter(os.path.isfile, os.listdir(tmp_dir)))
        for latex_image in files:
            if outformat == 'source':
                shutil.copy2(latex_image, dest_dir)
            else:
                filebase, _ = os.path.splitext(latex_image)
                latex_image_pdf = "{}.pdf".format(filebase)
                latex_image_svg = "{}.svg".format(filebase)
                latex_image_png = "{}.png".format(filebase)
                latex_image_eps = "{}.eps".format(filebase)
                latex_cmd = ["pdflatex", "-interaction=batchmode", latex_image]
                subprocess.call(latex_cmd, stdout=devnull, stderr=subprocess.STDOUT)
                pcm_cmd = ["pdf-crop-margins", latex_image_pdf, "-o", "cropped-"+latex_image_pdf, "-p", "0", "-a", "-1"]
                subprocess.call(pcm_cmd, stdout=devnull, stderr=subprocess.STDOUT)
                shutil.move("cropped-"+latex_image_pdf, latex_image_pdf)
                if outformat == 'all':
                    shutil.copy2(latex_image, dest_dir)
                if (outformat == 'pdf' or outformat == 'all'):
                    shutil.copy2(latex_image_pdf, dest_dir)
                if (outformat == 'svg' or outformat == 'all'):
                    svg_cmd =['pdf2svg', latex_image_pdf, latex_image_svg]
                    subprocess.call(svg_cmd)
                    shutil.copy2(latex_image_svg, dest_dir)
    shutil.rmtree(tmp_dir, ignore_errors=False)


def webwork(ptxfile, dest_dir, params, server_params):
    raise Exception('webwork temporarily removed')
    import os, shutil
    # Assume passed paths are absolute.
    # Set directory for WW representations.
    # dest_dir = os.path.join(dest_dir, outfile)
    utils.ensure_directory(dest_dir)

    # call the webwork-to-xml routine from core
    # the fourth argument seems to be for debugging on the ptx core side
    # the fifth argument has to do with ww server config; here just use
    # the default/recommended config in PreTeXt Guide. But this is passed as one of the collection of stringparams, so set to None here.  Sams for the pub_file.
    from . import core as ptxcore
    ptxcore.webwork_to_xml(xml_source=ptxfile, pub_file=None, stringparams=params, abort_early=True, server_params=server_params, dest_dir=dest_dir)

# This start of a utility function to replicate the tasks for xsltproc.
def xsltproc(xslfile, xmlfile, outfile=None, outdir=".", stringparams={}):
    dom = ET.parse(xmlfile)

    utils._verbose('XSL conversion of {} by {}'.format(xmlfile, xslfile))
    debug_string = 'XSL conversion via {} of {} to {} and/or into directory {} with parameters {}'
    utils._debug(debug_string.format(xslfile, xmlfile, outfile, outdir, stringparams))

    # print(stringparams['publisher'])

    # string parameters arrive in a "plain" string:string dictionary
    # but the values need to be prepped for lxml use, always
    stringparams = {key: ET.XSLT.strparam(value) for (
        key, value) in stringparams.items()}
    # xinclude:
    dom.xinclude()

    xslt = ET.parse(xslfile)
    utils._verbose('Loading the transform')
    transform = ET.XSLT(xslt)
    utils._verbose('Transforming the source')
    with utils.working_directory(outdir):
        newdom = transform(dom, **stringparams)
        #grab the format from xslfile and use it to name logfile:
        # logfile = xslfile[xslfile.find('pretext-'):].replace('pretext-','').replace('.xsl','')+'-build.log'
        # report any errors
        messages = transform.error_log
        if messages:
            logfile = "build.log"
            with open(logfile,"w") as log:
                log.write(str('Messages from application of {}:'.format(xslfile))+'\n')
                print('Messages from application of {}:'.format(xslfile))
                for m in messages:
                    log.write(m.message + '\n')
                    print(m.message)
        # Write output if not done by exsl:document:
        if outfile:
            utils._verbose('Writing output to file specified')
            with open(outfile, "w", encoding='utf-8') as fh:
                fh.write(str(newdom))

