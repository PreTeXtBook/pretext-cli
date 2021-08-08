import os
import random
import json
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler
import shutil
import socketserver
import socket
import logging
import threading
import watchdog.events, watchdog.observers, time
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


# Grabs project directory based on presence of `project.ptx`
def project_path(dirpath=os.getcwd()):
    if os.path.isfile(os.path.join(dirpath,'project.ptx')):
        # we're at the project root
        return dirpath
    parentpath = os.path.dirname(dirpath)
    if parentpath == dirpath:
        # cannot ascend higher, no project found
        return None
    else:
        # check parent instead
        return project_path(dirpath=parentpath)

def project_xml(dirpath=os.getcwd()):
    if project_path(dirpath) is None:
        project_manifest = static.path('templates','project.ptx')
    else:
        project_manifest = os.path.join(project_path(dirpath), 'project.ptx')
    return ET.parse(project_manifest)

def target_xml(alias=None,dirpath=os.getcwd()):
    if alias is None:
        return project_xml().find("targets/target")
    xpath = f'targets/target[@name="{alias}"]'
    matches = project_xml().xpath(xpath)
    if len(matches) == 0:
        log.info(f"No targets with alias {alias} found in project manifest file project.ptx.")
        return None
    return project_xml().xpath(xpath)[0]

def text_from_project_xml(xpath,default=None):
    matches = project_xml().xpath(xpath)
    if len(matches) > 0:
        return matches[0].text.strip()
    else:
        return default

#check xml syntax
def xml_syntax_is_valid(xmlfile):
    # parse xml
    try:
        source_xml = ET.parse(xmlfile)
        # we need to call xinclude once for each level of nesting (just to check for errors).  25 levels should be more than sufficient
        for i in range(25):
            source_xml.xinclude()
        log.debug('XML syntax appears well formed.')
        if (source_xml.getroot().tag != 'pretext'):
            log.error(f'The file {xmlfile} does not have "<pretext>" as its root element.  Did you use a subfile as your source?  Check the project manifest (project.ptx).')
            return False
    # check for file IO error
    except IOError:
        log.error(f'The file {xmlfile} does not exist')
        return False

    # check for XML syntax errors
    except ET.XMLSyntaxError as err:
        log.error('XML Syntax Error, see error_syntax.log. Quitting...')
        with open('error_syntax.log', 'w') as error_log_file:
            error_log_file.write(str(err.error_log))
        return False
    except ET.XIncludeError as err:
        log.error(
            'XML Syntax Error with instance of xinclude; see error_syntax.log. Quitting...')
        with open('error_syntax.log', 'w') as error_log_file:
            error_log_file.write(str(err.error_log))
        return False
    return True

def xml_source_validates_against_schema(xmlfile):
    #get path to RelaxNG schema file:
    schemarngfile = static.path('schema','pretext.rng')

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
        log.debug('PreTeXt document did not pass schema validation; unexpected output may result. See .error_schema.log for hints.  Continuing with build.')
        with open('.error_schema.log', 'w') as error_log_file:
            error_log_file.write(str(err.error_log))
        return False
    return True

# watchdog handler for watching changes to source
class HTMLRebuildHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self,callback):
        self.last_trigger_at = time.time()-5
        self.callback = callback
    def on_any_event(self,event):
        # only trigger at most every 5 seconds
        if time.time() > self.last_trigger_at + 5:
            self.last_trigger_at = time.time()
            log.info(f"\nChanges to source detected.\n")
            self.callback()

# boilerplate to prevent overzealous caching by preview server, and
# avoid port issues
def binding_for_access(access="private"):
    if os.path.isfile("/home/user/.smc/info.json") or access=="public":
        return "0.0.0.0"
    else:
        return "localhost"
def url_for_access(access="private",port=8000):
    if os.path.isfile("/home/user/.smc/info.json"):
        project_id = json.loads(open('/home/user/.smc/info.json').read())['project_id']
        return f"https://cocalc.com/{project_id}/server/{port}/"
    elif access=='public':
        return f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        return f"http://localhost:{port}"
def serve_forever(directory,access="private",port=8000):
    log.info(f"Now starting a server to preview directory `{directory}`.\n")
    binding = binding_for_access(access)
    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        """HTTP request handler with no caching"""
        def end_headers(self):
            self.send_my_headers()
            SimpleHTTPRequestHandler.end_headers(self)
        def send_my_headers(self):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
    class TCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    looking_for_port = True
    while looking_for_port:
        try:
            with TCPServer((binding, port), RequestHandler) as httpd:
                looking_for_port = False
                url = url_for_access(access,port)
                log.info(f"Server started at {url}\n")
                log.info("Use [Ctrl]+[C] to halt the server.\n")
                httpd.serve_forever()
        except OSError:
            log.warning(f"Port {port} could not be used.")
            port = random.randint(49152,65535)
            log.warning(f"Trying port {port} instead.\n")

def run_server(directory,access,port,watch_directory=None,watch_callback=lambda:None):
    binding = binding_for_access(access)
    threading.Thread(target=lambda: serve_forever(directory,access,port),daemon=True).start()
    if watch_directory is not None:
        log.info(f"\nWatching for changes in `{watch_directory}` ...\n")
        event_handler = HTMLRebuildHandler(watch_callback)
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, watch_directory, recursive=True)
        observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\nClosing server...")
        if watch_directory is not None: observer.stop()
    if watch_directory is not None: observer.join()

# Info on namespaces: http://lxml.de/tutorial.html#namespaces
NSMAP = {
    "xi": "http://www.w3.org/2001/XInclude",
    "xml": "http://www.w3.org/XML/1998/namespace",
}
def nstag(prefix,suffix):
    return "{" + NSMAP[prefix] + "}" + suffix

def expand_pretext_href(lxml_element):
    '''
    Expands @pretext-href attributes to point to the distributed xsl directory.
    '''
    for ele in lxml_element.xpath('//*[@pretext-href]'):
        ele.set('href',str(static.core_xsl(ele.get('pretext-href'),as_path=True)))

def copy_fix_xsl(xsl_path, output_dir):
    xsl_dir = os.path.abspath(os.path.dirname(xsl_path))
    output_dir = os.path.abspath(output_dir)
    with working_directory(xsl_dir):
        for filename in os.listdir('.'):
            if filename.endswith('.xsl'):
                lxml_element = ET.parse(filename)
                expand_pretext_href(lxml_element)
                output_path = os.path.join(output_dir, filename)
                lxml_element.write(output_path)
            elif filename.endswith('.ent'):
                # an author might include a copy of the .ent file which should also be copied.
                shutil.copyfile(filename, os.path.join(output_dir, filename))
