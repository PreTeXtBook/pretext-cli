from lxml import etree as ET

from . import static, document, utils



def build_html(ptxfile,output,stringparams):
    import os
    # from pathlib import Path
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = static.filepath('pretext-html.xsl')
    # create output directories and move there.
    # output = os.path.abspath(output)
    utils.ensure_directory(output)
    os.chdir(output)  # change to output dir.
    utils.ensure_directory('knowl')
    utils.ensure_directory('images')
    # transform ptx using xsl:
    xsltproc(xslfile, ptxfile, stringparams)


def build_latex(ptxfile,output,stringparams):
    import os
    # import sys
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = static.filepath('pretext-latex.xsl')
    #create output directory
    # output = os.path.abspath(output)
    utils.ensure_directory(output)
    os.chdir(output)
    # Do the xsltproc equivalent:
    # params = {"latex.font.size": "'20pt'"}
    xsltproc(xslfile, ptxfile, stringparams, outfile='main.tex')




# This start of a utility function to replicate the tasks for xsltproc.
# TODO: add string params.  Here stringparams defaults to an empty dictionary.
def xsltproc(xslfile, xmlfile, stringparams={}, outfile=None):
    dom = ET.parse(xmlfile)
    try:
        dom.xinclude()
    except:
        print('there was an error with xinclude')
    print('Read in xsl file at', xslfile)
    xslt = ET.parse(xslfile)
    print('Load the transform')
    transform = ET.XSLT(xslt)
    print('Transform the source')
    newdom = transform(dom, **stringparams)
    print(transform.error_log)
    if outfile:
        print('writing output to file specified')
        with open(outfile, "w") as fh:
            fh.write(str(newdom))
