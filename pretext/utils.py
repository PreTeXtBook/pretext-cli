import os
from contextlib import contextmanager
import configobj
from http.server import SimpleHTTPRequestHandler
import logging
from lxml import etree as ET

from . import static

# Get access to logger
log = logging.getLogger('ptxlogger')

@contextmanager
def working_directory(path):
    """
    Temporarily change the current working directory.

    Usage:
    with working_directory(path):
        do_things()   # working in the given path
    do_other_things() # back to original path
    """
    current_directory=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current_directory)


def ensure_directory(path):
    """
    If the directory doesn't exist yet, create it.
    """
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def directory_exists(path):
    """
    Checks if the directory exists.
    """
    return os.path.exists(path)

# Write config file
def write_config(configfile, **kwargs):
    config = configobj.ConfigObj(configfile, unrepr=True)
    # config.filename = configfile
    # config["source"] = source
    # config["output"] = output
    # etc:
    for key, value in kwargs.items():
        config[key] = value
    config.write()
    log.info("Saving options to the config file {}".format(configfile))
    with open(configfile) as cf:
        print(cf.read())

#check xml syntax


def xml_syntax_check(xmlfile):
    # parse xml
    try:
        source_xml = ET.parse(xmlfile)
        # we need to call xinclude once for each level of nesting (just to check for errors).  25 levels should be more than sufficient
        for i in range(25):
            source_xml.xinclude()
        log.info('XML syntax appears well formed.')

    # check for file IO error
    except IOError:
        log.error('Invalid File')

    # check for XML syntax errors
    except ET.XMLSyntaxError as err:
        log.error('XML Syntax Error, see error_syntax.log. Quitting...')
        with open('error_syntax.log', 'w') as error_log_file:
            error_log_file.write(str(err.error_log))
        quit()
    except ET.XIncludeError as err:
        log.error(
            'XML Syntax Error with instance of xinclude; see error_syntax.log. Quitting...')
        with open('error_syntax.log', 'w') as error_log_file:
            error_log_file.write(str(err.error_log))
        quit()

def schema_validate(xmlfile):
    #get path to RelaxNG schema file:
    static_dir = os.path.dirname(static.__file__)
    schemarngfile = os.path.join(static_dir, 'schema', 'pretext.rng')

    # Open schemafile for validation:
    relaxng = ET.RelaxNG(file=schemarngfile)

    # Parse xml file:
    source_xml = ET.parse(xmlfile)

    ## just for testing:
    # relaxng.validate(source_xml)
    # log = relaxng.error_log
    # print(log)

    # validate against schema
    try:
        relaxng.assertValid(source_xml)
        log.info('PreTeXt source passed schema validation.')

    except ET.DocumentInvalid as err:
        log.warning('PreTeXt document did not pass schema validation; unexpected output may result. See error_schema.log for hints.  Continuing with build.')
        with open('error_schema.log', 'w') as error_log_file:
            error_log_file.write(str(err.error_log))
        pass


class NoCacheHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with no caching"""
    def end_headers(self):
        self.send_my_headers()
        SimpleHTTPRequestHandler.end_headers(self)
    def send_my_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")


# Info on namespaces: http://lxml.de/tutorial.html#namespaces
NSMAP = {
    "xi": "http://www.w3.org/2001/XInclude",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
def nstag(prefix,suffix):
    return "{" + NSMAP[prefix] + "}" + suffix
