import os
import glob
import random
import json
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler
import shutil
import pathlib
import socketserver
import socket
import logging
import threading
import watchdog.events, watchdog.observers, time
from lxml import etree as ET

from . import static
from .static.pretext import pretext as core

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
    log.debug(f"Now working in directory {path}")
    try:
        yield
    finally:
        os.chdir(current_directory)
        log.debug(f"Successfully changed directory back to {current_directory}")

def linux_path(path):
    # hack to make core ptx and xsl:import happy
    p = pathlib.Path(path)
    return p.as_posix()


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

def requirements_version(dirpath=os.getcwd()):
    try:
        with open(os.path.join(project_path(dirpath),'requirements.txt'),'r') as f:
            for line in f.readlines():
                if 'pretextbook' in line:
                    return line.split("==")[1].strip()
    except Exception as e:
        log.debug("Could not read `requirements.txt`:")
        log.debug(e)
        return None

def project_xml_string(dirpath=os.getcwd()):
    return ET.tostring(project_xml(dirpath), encoding='unicode')

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
        log.error('XML Syntax Error caused build to fail:')
        log.error(str(err.error_log))
        return False
    except ET.XIncludeError as err:
        log.error('XInclude Error caused build to fail:')
        log.error(str(err.error_log))
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
        self.last_trigger_at = time.time()
        # only run callback once triggers halt for a second
        def timeout_callback(handler):
            time.sleep(1.5)
            if time.time() > handler.last_trigger_at + 1:
                handler.last_trigger_at = time.time()
                log.info("\nChanges to source detected.\n")
                handler.callback()
        threading.Thread(target=timeout_callback,args=(self,)).start()

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
                log.info(f"Success! Open the below url in a web browser to preview the most recent build of your project.")
                log.info("    "+url)
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
        ele.set('href',str(linux_path(static.core_xsl(ele.get('pretext-href'),as_path=True))))

def copy_expanded_xsl(xsl_path: str, output_dir: str):
    """
    Copy relevant files that share a directory with `xsl_path`
    while pre-processing the `.xsl` files.
    """
    xsl_dir = os.path.abspath(os.path.dirname(xsl_path))
    output_dir = os.path.abspath(output_dir)
    log.debug(f"Copying all files in {xsl_dir} to {output_dir}")
    shutil.copytree(xsl_dir, output_dir, dirs_exist_ok=True)
    # expand each xsl file
    with working_directory(output_dir):
        for filename in glob.iglob('**',recursive=True):
            # glob lists both files and directories, but we only want to copy files.
            if os.path.isfile(filename) and filename.endswith('.xsl'):
                log.debug(f"Expanding and copying {filename}")
                try:
                    lxml_element = ET.parse(filename)
                    expand_pretext_href(lxml_element)
                    lxml_element.write(filename)
                # maybe an xsl file is malformed, but let's continue in case it's unused
                except Exception as e:
                    log.warning(f"Hit error `{e}` when expanding {filename}, continuing anyway...")

def check_executable(exec_name):
    try:
        exec_cmd = core.get_executable_cmd(exec_name)[0]
        log.debug(f"PTX-CLI: Executable command {exec_name} found at {exec_cmd}")
        return exec_cmd
    except OSError as e:
        log.debug(e)

def check_asset_execs(element, outformats=None):
    # outformats is assumed to be a list of formats.
    if outformats is None:
        outformats = []
    # Note that asymptote is done via server, so doesn't require asy.  We could check for an internet connection here for that and webwork, etc.
    log.debug(f"trying to check assets for {element} and output format {outformats}")
    # Create list of executables needed based on output format
    required_execs = []
    if element == "latex-image":
        required_execs = ['xelatex']
        if 'svg' in outformats or 'all' in outformats:
            required_execs.append('pdfsvg')
        if 'png' in outformats or 'all' in outformats:
            required_execs.append('pdfpng')
        if 'eps' in outformats or 'all' in outformats:
            required_execs.append('pdfeps')
    if element == "sageplot":
        required_execs = ['sage']
    if element == "interactive":
        required_execs = ['pageres']
    install_hints = {
        'xelatex':{
            'Windows': 'See https://pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''},
        'pdfsvg': {
            'Windows': 'Follow the instructions at https://pretextbook.org/doc/guide/html/section-installing-pdf2svg.html to install pdf2svg',
            'Darwin': '',
            'Linux': 'You should be able to install pdf2svg with your package manager (e.g., `sudo apt install pdf2svg`.  See https://github.com/dawbarton/pdf2svg#pdf2svg.'},
        'pdfpng': {
            'Windows': 'See https:// pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''},
        'pdfeps': {
            'Windows': 'See https:// pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''},
        'sage': {
            'Windows': 'See https://doc.sagemath.org/html/en/installation/index.html#windows',
            'Darwin': 'https://doc.sagemath.org/html/en/installation/index.html#macos',
            'Linux': 'See https://doc.sagemath.org/html/en/installation/index.html#linux'},
        'pageres': {
            'Windows': 'See https:// pretextbook.org/doc/guide/html/windows-cli-software.html',
            'Darwin': '',
            'Linux': ''}
        }
    for required_exec in required_execs:
        if check_executable(required_exec) is None:
            log.warning(f"In order to generate {element} into formats {outformats}, you must have {required_exec} installed, but this appears to be missing or configured incorrectly in pretext.ptx")
            #print installation hints based on operating system and missing program.
            log.info(install_hints[required_exec][platform.system()])
    