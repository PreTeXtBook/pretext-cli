from lxml import etree as ET
import os, sys, shutil
import logging
import git
from . import static, utils
from . import build as builder
from .static.pretext import pretext as core

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
                 project_path=None):
        if project_path is None:
            project_path = os.getcwd()
        if xml_element is None:
                static_dir = os.path.dirname(static.__file__)
                template_xml = os.path.join(static_dir,"templates","project.ptx")
                xml_element = ET.parse(template_xml).getroot().find("targets/target")
                publication = os.path.join(static_dir,"templates","project.ptx")
                for pub_ele in xml_element.xpath("publication"):
                    xml_element.remove(pub_ele)
                pub_ele = ET.SubElement(xml_element,"publication")
                pub_ele.text = publication
        if xml_element.tag != "target":
            raise ValueError("xml_element must have tag `target` as root")
        # construct self.xml_element
        # set name attribute
        if name is not None:
            xml_element.set("name",name)
        # set subelements with text nodes
        tag_pairs = [("format",format),("source",source),("publication",publication),("output-dir",output_dir)]
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

    def output_dir(self):
        return os.path.abspath(os.path.join(self.__project_path,self.xml_element().find("output-dir").text.strip()))

    def stringparams(self):
        return {
            sp_ele.get("key").strip(): sp_ele.get("value").strip()
            for sp_ele in self.xml_element().xpath("stringparam")
        }



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
                static_dir = os.path.dirname(static.__file__)
                template_xml = os.path.join(static_dir,"templates","project.ptx")
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
            for target_element in xml_element().xpath("targets/target")
        ]

    def target(self,name=None):
        if name is None:
            target_element=self.xml_element().find("targets/target")
        else:
            target_element=self.xml_element().find(f'targets/target[@name="{name}"]')
        if target_element is not None:
            return Target(xml_element=target_element)
        else:
            return None

    def view(self,target_name,access,port,watch):
        target = self.target(target_name)
        if not utils.directory_exists(target.output_dir()):
            log.error(f"The directory `{target.output_dir()}` does not exist. Maybe try `pretext build {target.name()}` first?")
            return
        directory = target.output_dir()
        if watch:
            watch_directory = target.source_dir()
            self.build(target_name)
        else:
            watch_directory = None
        watch_callback=lambda:self.build(target_name)
        utils.run_server(directory,access,port,watch_directory,watch_callback)

    def build(self,target_name,webwork=False,diagrams=False,diagrams_format="svg",only_assets=False):
        # prepre core PreTeXt pythons scripts
        self.init_ptxcore()
        # Check for xml syntax errors and quit if xml invalid:
        if not self.xml_source_syntax_is_valid(target_name):
            return
        # Validate xml against schema; continue with warning if invalid:
        self.xml_source_schema_is_valid(target_name)
        # Ensure directories for assets and generated assets to avoid errors when building:
        target = self.target(target_name)
        utils.ensure_directory(target.external_dir())
        utils.ensure_directory(target.generated_dir())
        #remove output directory so ptxcore doesn't complain.
        if os.path.isdir(target.output_dir()):
            shutil.rmtree(target.output_dir())
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
        if diagrams:
            builder.diagrams(target.source(), target.publication(), target.generated_dir(), target.stringparams(), diagrams_format)
        else:
            source_xml = target.source_xml()
            if target.format()=="html" and len(source_xml.xpath('//asymptote|//latex-image|//sageplot')) > 0:
                log.warning("There are generated images (<latex-image/>, <asymptote/>, or <sageplot/>) or in source, "+
                            "but these will not be (re)built. Run pretext build with the `-d` flag if updates are needed.")
            # TODO: remove the elements that are not needed for latex.
            if target.format()=="latex" and len(source_xml.xpath('//asymptote|//sageplot|//video[@youtube]|//interactive[not(@preview)]')) > 0:
                log.warning("The source has interactive elements or videos that need a preview to be generated, "+
                            "but these will not be (re)built. Run `pretext build` with the `-d` flag if updates are needed.")
        if target.format()=='html' and not only_assets:
            builder.html(target.source(),target.publication(),target.output_dir(),target.stringparams())
        if target.format()=='latex' and not only_assets:
            builder.latex(target.source(),target.publication(),target.output_dir(),target.stringparams())
            # core script doesn't put a copy of images in output for latex builds, so we do it instead here
            shutil.copytree(target.external_dir(),os.path.join(target.output_dir(),"external"))
            shutil.copytree(target.generated_dir(),os.path.join(target.output_dir(),"generated"))
        if target.format()=='pdf' and not only_assets:
            builder.pdf(target.source(),target.publication(),target.output_dir(),target.stringparams())

    def publish(self,target_name):
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
            repo.git.commit(message="Update to PreTeXt project source.")
        try:
            origin = repo.remote('origin')
        except ValueError:
            log.error("Repository must have an `origin` remote pointing to GitHub.")
            return
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
            log.error("Latest build is the same as last published build.")
            return
        log.info("Pushing to GitHub. (Your password may be required below.)")
        origin.push()
        log.info(f"Latest build successfully pushed to GitHub.")
        log.info("(It may take a few seconds for GitHub Pages to reflect any changes.)")

    def xml_source_syntax_is_valid(self,target_name):
        target = self.target(target_name)
        return utils.xml_syntax_is_valid(target.source())

    def xml_source_schema_is_valid(self,target_name):
        target = self.target(target_name)
        return utils.xml_schema_is_valid(target.source())

    def executables(self):
        return {
            ele.tag: ele.text
            for ele in self.xml_element().xpath("executables/*")
        }

    def init_ptxcore(self):
        core.set_executables(self.executables())
