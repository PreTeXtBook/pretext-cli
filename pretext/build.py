from lxml import etree as ET

from . import static, document, utils



def html(ptxfile,output,stringparams):
    # from pathlib import Path
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = static.filepath('pretext-html.xsl')
    # create output directories and move there.
    # output = os.path.abspath(output)
    utils.ensure_directory(output)
    with utils.working_directory(output):
        utils.ensure_directory('knowl')
        utils.ensure_directory('images')
    # transform ptx using xsl:
    xsltproc(xslfile, ptxfile, outfile=None, outdir=output, stringparams=stringparams)


def latex(ptxfile,output,stringparams):
    # import sys
    # ptxfile = os.path.abspath('source/main.ptx')
    xslfile = static.filepath('pretext-latex.xsl')
    #create output directory
    # output = os.path.abspath(output)
    utils.ensure_directory(output)
    # Do the xsltproc equivalent:
    # params = {"latex.font.size": "'20pt'"}
    xsltproc(xslfile, ptxfile, outfile='main.tex', outdir=output, stringparams=stringparams)




# This start of a utility function to replicate the tasks for xsltproc.
def xsltproc(xslfile, xmlfile, outfile=None, outdir=".", stringparams={}):
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
    with utils.working_directory(outdir):
        newdom = transform(dom, **stringparams)
        logfile = xslfile[xslfile.find('pretext-'):].replace('pretext-','').replace('.xsl','')+'-build.log'
        print(transform.error_log)
        with open(logfile,"w") as log:
            log.write(str(transform.error_log))
        if outfile:
            print('writing output to file specified')
            with open(outfile, "w") as fh:
                fh.write(str(newdom))
