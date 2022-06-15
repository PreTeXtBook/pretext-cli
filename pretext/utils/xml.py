import glob
import os
import shutil
from lxml import etree as ET
import logging
from .. import static

# Get access to logger
log = logging.getLogger('ptxlogger')

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