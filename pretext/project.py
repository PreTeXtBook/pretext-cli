from lxml import etree as ET
import os, shutil
import logging
import tempfile
import git
from . import static, utils
from . import build as builder
from .static.pretext import pretext as core
from pathlib import Path

log = logging.getLogger('ptxlogger')

class Target():
    def __init__(self,
                 xml_element=None,
                 name=None,
                 format=None,
                 source=None,
                 publication=None,
                 output_dir=None,
                 stringparams=None,
                 xsl_path=None,
                 project_path=None):
        if project_path is None:
            project_path = os.getcwd()
        if xml_element is None:
            template_xml = static.path("templates","project.ptx")
            xml_element = ET.parse(template_xml).getroot().find("targets/target")
            publication_path = static.path("templates","publication.ptx")
            for pub_ele in xml_element.xpath("publication"):
                pub_ele.text = publication_path
        if xml_element.tag != "target":
            raise ValueError("xml_element must have tag `target` as root")
        # construct self.xml_element
        # set name attribute
        if name is not None:
            xml_element.set("name",name)
        # set subelements with text nodes
        tag_pairs = [("format",format),("source",source),("publication",publication),("output-dir",output_dir),("xsl",xsl_path)]
        for tag,ele_text in tag_pairs:
            if ele_text is not None:
                for tag_element in xml_element.xpath(tag):
                    xml_element.remove(tag_element)
                tag_element = ET.SubElement(xml_element,tag)
                tag_element.text = ele_text.strip()
        # set several stringparam subelements with key/value attributes
        if stringparams is not None:
            for sp_element in xml_element.xpath("stringparam"):
                xml_element.remove(sp_element)
            for key,val in stringparams.items():
                sp_element = ET.SubElement(xml_element,"stringparam")
                sp_element.set("key",key.strip())
                sp_element.set("value", val.strip())
        # construction is done!
        self.__xml_element = xml_element
        self.__project_path = project_path

    def xml_element(self):
        return self.__xml_element

    def name(self):
        return self.xml_element().get("name").strip()

    def format(self):
        return self.xml_element().find("format").text.strip()

    def source(self):
        return os.path.abspath(os.path.join(self.__project_path,self.xml_element().find("source").text.strip()))

    def source_dir(self):
        return os.path.dirname(self.source())

    def source_xml(self):
        ele_tree = ET.parse(self.source())
        ele_tree.xinclude()
        return ele_tree.getroot()

    def publication(self):
        return os.path.abspath(os.path.join(self.__project_path,self.xml_element().find("publication").text.strip()))

    def publication_dir(self):
        return os.path.dirname(self.publication())

    def publication_rel_from_source(self):
        return os.path.relpath(self.publication(),self.source_dir())

    def publication_xml(self):
        ele_tree = ET.parse(self.publication())
        ele_tree.xinclude()
        return ele_tree.getroot()

    def external_dir(self):
        dir_ele = self.publication_xml().find("source/directories")
        if dir_ele is None:
            log.error("Publication file does not specify asset directories.")
            return None
        rel_dir = dir_ele.get("external")
        return os.path.join(self.source_dir(),rel_dir)

    def generated_dir(self):
        dir_ele = self.publication_xml().find("source/directories")
        if dir_ele is None:
            log.error("Publication file does not specify asset directories.")
            return None
        rel_dir = dir_ele.get("generated")
        return os.path.join(self.source_dir(),rel_dir)

    def webwork_representations_path(self):
        dir_ele = self.publication_xml().find("source[@webwork-problems]")
        if dir_ele is None:
            log.debug("Publication file does not specify webwork-representation.ptx file")
            return None
        rel_dir = dir_ele.get("webwork-problems")
        return os.path.join(self.source_dir(),rel_dir)

    def output_dir(self):
        return os.path.abspath(os.path.join(self.__project_path,self.xml_element().find("output-dir").text.strip()))

    def stringparams(self):
        return {
            sp_ele.get("key").strip(): sp_ele.get("value").strip()
            for sp_ele in self.xml_element().xpath("stringparam")
        }
    
    def xsl_path(self):
        if self.xml_element().find("xsl") is not None:
            return os.path.abspath(os.path.join(self.__project_path, self.xml_element().find("xsl").text.strip()))
        else:
            return None



class Project():
    def __init__(self,
                 xml_element=None,
                 targets=None,
                 project_path=None):
        if project_path is None:
            project_path = os.getcwd()
        if xml_element is None:
            if utils.project_path() is not None:
                xml_element = ET.parse(os.path.join(utils.project_path(),"project.ptx")).getroot()
            else:
                template_xml = static.path("templates","project.ptx")
                xml_element = ET.parse(template_xml).getroot()
        else:
            if xml_element.tag != "project":
                raise ValueError("xml_element must have tag `project` as root")
        if targets is not None:
            for targets_element in xml_element.xpath("targets"):
                xml_element.remove(targets_element)
            targets_element = ET.SubElement(xml_element,"targets")
            for target in targets:
                targets_element.append(target.xml_element())
        self.__xml_element = xml_element
        self.__project_path = project_path

    def xml_element(self):
        return self.__xml_element

    def targets(self):
        return [
            Target(xml_element=target_element,project_path=self.__project_path)
            for target_element in self.xml_element().xpath("targets/target")
        ]

    def print_target_names(self):
        for target in self.targets():
            print(target.name())

    def target(self,name=None):
        if name is None:
            target_element=self.xml_element().find("targets/target")
        else:
            target_element=self.xml_element().find(f'targets/target[@name="{name}"]')
        if target_element is not None:
            return Target(xml_element=target_element)
        else:
            return None

    def view(self,target_name,access,port,watch=False,build=False):
        target = self.target(target_name)
        directory = target.output_dir()
        if watch or build:
            log.info("Building target...")
            self.build(target_name)
        if watch:
            watch_directory = target.source_dir()
        else:
            watch_directory = None
        if not utils.directory_exists(target.output_dir()):
            log.error(f"The directory `{target.output_dir()}` does not exist. Maybe try `pretext build {target.name()}` first?")
            return
        watch_callback=lambda:self.build(target_name)
        utils.run_server(directory,access,port,watch_directory,watch_callback)

    def build(self,target_name,webwork=False,diagrams=False,diagrams_format='defaults',only_assets=False,clean=False):
        # prepre core PreTeXt pythons scripts
        self.init_ptxcore()
        # Check for xml syntax errors and quit if xml invalid:
        if not self.xml_source_is_valid(target_name):
            return
        if not self.xml_publication_is_valid(target_name):
            return
        # Validate xml against schema; continue with warning if invalid:
        self.xml_schema_validate(target_name)
        # Ensure directories for assets and generated assets to avoid errors when building:
        target = self.target(target_name)
        utils.ensure_directory(target.external_dir())
        utils.ensure_directory(target.generated_dir())
        # Check for WeBWorK but not webwork-representations file:
        if len(target.source_xml().xpath('//webwork'))>0:
            if target.webwork_representations_path() is None:
                log.warning(f'Your source contains WeBWorK exercises but you do not have a "webwork-representations" file specified in your publication file.  Modify your publication file and run `pretext build -w`.')
            elif not os.path.isfile(target.webwork_representations_path()):
                log.warning(f'Your source contains WeBWorK exercises the path to the "webwork-representations.ptx" file in your publication file does not point to a file. Run `pretext build -w` or modify your publication file.')
        # refuse to clean if output is not a subdirectory of the working directory or contains source/publication
        if clean:
            if Path(self.__project_path) not in Path(target.output_dir()).parents:
                log.warning("Refusing to clean output directory that isn't a proper subdirectory of the project.")
            elif Path(target.output_dir()) in Path(os.path.join(target.source_dir(),"foo")).parents or \
                Path(target.output_dir()) in Path(os.path.join(target.publication_dir(),"foo")).parents:
                log.warning("Refusing to clean output directory that contains source or publication files.")
            else:
                log.warning(f"Destorying directory {target.output_dir()} to clean previously built files.")
                shutil.rmtree(target.output_dir())
        #build in temporary directory so ptxcore doesn't complain
        with tempfile.TemporaryDirectory() as temp_dir:
            log.info(f"Preparing to build into a temporary directory.")
            # copy custom xsl if used
            custom_xsl = None
            if target.xsl_path() is not None:
                log.info(f'Building with custom xsl {target.xsl_path()} specified in project.ptx')
                utils.copy_fix_xsl(target.xsl_path(), temp_dir)
                custom_xsl = os.path.join(temp_dir, os.path.basename(target.xsl_path()))
            #build targets:
            if webwork:
                # prepare params; for now assume only server is passed
                # see documentation of pretext core webwork_to_xml
                # handle this exactly as in webwork_to_xml (should this
                # be exported in the pretext core module?)
                webwork_output = os.path.join(target.generated_dir(),'webwork')
                utils.ensure_directory(webwork_output)
                try:
                    server_url = target.stringparams()['server']
                except Exception as e:
                    root_cause = str(e)
                    server_url = "https://webwork-ptx.aimath.org"
                    log.warning(f"No server name, {root_cause}.")
                    log.warning(f"Using default {server_url}")
                builder.webwork(target.source(), target.publication(), webwork_output, target.stringparams(), server_url)
            elif len(target.source_xml().xpath('//webwork')) > 0:
                log.warning(
                    "The source has WeBWorK exercises, but you are not re(processing) these.  Run `pretext build` with the `-w` flag if updates are needed.")
            if diagrams:
                builder.diagrams(target.source(), target.publication(), target.generated_dir(), target.stringparams(), target.format(), diagrams_format)
            else:
                source_xml = target.source_xml()
                if target.format()=="html" and len(source_xml.xpath('//asymptote|//latex-image|//sageplot')) > 0:
                    log.warning("The source has generated images (<latex-image/>, <asymptote/>, or <sageplot/>), "+
                                "but these will not be (re)built. Run `pretext build` with the `-d` flag if updates are needed.")
                if target.format()=="latex" and len(source_xml.xpath('//asymptote|//sageplot|//video[@youtube]|//interactive[not(@preview)]')) > 0:
                    log.warning("The source has interactive elements or videos that need a preview to be generated, "+
                                "but these will not be (re)built. Run `pretext build` with the `-d` flag if updates are needed.")
            if target.format()=='html' and not only_assets:
                try:
                    builder.html(target.source(),target.publication(),temp_dir,target.stringparams(),custom_xsl)
                except Exception as e:
                    log.debug(f"Critical error info:\n", exc_info=True)
                    log.critical(
                        f"A fatal error has occurred:\n {e} \nFor more info, run pretext with `-v debug`")
                    return
            if target.format()=='latex' and not only_assets:
                try:
                    builder.latex(target.source(),target.publication(),temp_dir,target.stringparams(),custom_xsl)
                    # core script doesn't put a copy of images in output for latex builds, so we do it instead here
                    shutil.copytree(target.external_dir(),os.path.join(temp_dir,"external"))
                    shutil.copytree(target.generated_dir(),os.path.join(temp_dir,"generated"))
                except Exception as e:
                    log.debug(f"Critical error info:\n", exc_info=True)
                    log.critical(
                        f"A fatal error has occurred:\n {e} \nFor more info, run pretext with `-v debug`")
                    return
            if target.format()=='pdf' and not only_assets:
                try:
                    builder.pdf(target.source(),target.publication(),temp_dir,target.stringparams(),custom_xsl)
                except Exception as e:
                    log.debug(f"Critical error info:\n", exc_info=True)
                    log.critical(
                        f"A fatal error has occurred:\n {e} \nFor more info, run pretext with `-v debug`")
                    return
            # build was successful, so copy contents of temporary directory to actual directory
            log.info(f"\nCopying successful build from {temp_dir} into {target.output_dir()}.")
            shutil.copytree(temp_dir,target.output_dir(),dirs_exist_ok=True)
            log.info(f"\nSuccess! Run `pretext view {target.name()}` to see the results.\n")

    def publish(self,target_name,commit_message="Update to PreTeXt project source."):
        target = self.target(target_name)
        if target.format() != "html":
            log.error("Only HTML format targets are supported.")
            return
        try:
            repo = git.Repo(self.__project_path)
        except git.exc.InvalidGitRepositoryError:
            log.error("Target's project must be under Git version control.")
            return
        if repo.bare or repo.is_dirty() or len(repo.untracked_files)>0:
            log.info("Updating project Git repository with latest changes to source.")
            repo.git.add(all=True)
            repo.git.commit(message=commit_message)
        if not utils.directory_exists(target.output_dir()):
            log.error(f"The directory `{target.output_dir()}` does not exist. Maybe try `pretext build` first?")
            return
        log.info(f"Preparing to publish the latest build located in `{target.output_dir()}`.")
        docs_path = os.path.join(self.__project_path,"docs")
        shutil.rmtree(docs_path,ignore_errors=True)
        shutil.copytree(target.output_dir(),docs_path)
        log.info(f"Latest build copied to `{docs_path}`.")
        repo.git.add('docs')
        try:
            repo.git.commit(message=f"Publish latest build of target {target.name()}.")
        except git.exc.GitCommandError:
            log.warning("Latest build is the same as last published build.")
            pass
        log.info("Pushing to GitHub. (Your password may be required below.)")
        try:
            repo.git.push()
        except git.exc.GitCommandError:
            log.error("Unable to push to GitHub.  Try running `git push` yourself.")
            return
        log.info(f"Latest build successfully pushed to GitHub.")
        log.info("(It may take a few seconds for GitHub Pages to reflect any changes.)")

    def xml_source_is_valid(self,target_name):
        target = self.target(target_name)
        return utils.xml_syntax_is_valid(target.source())

    def xml_schema_validate(self,target_name):
        target = self.target(target_name)
        return utils.xml_source_validates_against_schema(target.source())

    def xml_publication_is_valid(self,target_name):
        target = self.target(target_name)
        try:
            publication_xml = ET.parse(target.publication())
            # Would we ever have a publication with xi:include?  Just in case...
            publication_xml.xinclude()
        except Exception as e:
            log.critical(f'Unable to read publication file.  Quitting. {e}')
            log.debug('', exc_info=True)
            return False
        if (publication_xml.getroot().tag != 'publication'):
            log.error(f'The publication file {target.publication()} must have "<publication>" as its root element.')
            return False
        return True

    def executables(self):
        return {
            ele.tag: ele.text
            for ele in self.xml_element().xpath("executables/*")
        }

    def init_ptxcore(self):
        core.set_executables(self.executables())
