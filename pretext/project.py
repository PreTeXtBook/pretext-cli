from lxml import etree as ET
import os, sys, shutil
import logging
import git
from . import static, utils

log = logging.getLogger('ptxlogger')

class Target():
    def __init__(self,
                 xml_element=None,
                 name=None,
                 format=None,
                 source=None,
                 publication=None,
                 output_dir=None,
                 stringparams_dict=None,
                 project_path=None):
        if project_path is None:
            project_path = os.getcwd()
        if xml_element is None:
                static_dir = os.path.dirname(static.__file__)
                template_xml = os.path.join(static_dir,"templates","project.ptx")
                xml_element = ET.parse(template_xml).getroot().find("targets/target")
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
        if stringparams_dict is not None:
            for sp_element in xml_element.xpath("stringparam"):
                xml_element.remove(sp_element)
            for key,val in stringparams_dict.items():
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

    def publication(self):
        return os.path.abspath(os.path.join(self.__project_path,self.xml_element().find("publication").text.strip()))

    def output_dir(self):
        return os.path.abspath(os.path.join(self.__project_path,self.xml_element().find("output-dir").text.strip()))

    def stringparams(self):
        return {
            sp_ele.get("key").strip(): sp_ele.get("value").strip()
            for sp_ele in self.xml_element().xpath("stringparam")
        }

    def view(self,access,port,watch):
        if not utils.directory_exists(self.output_dir()):
            log.error(f"""
            The directory `{self.output_dir()}` does not exist.
            Maybe try `pretext build {self.name()}` first?
            """)
            return
        directory = self.output_dir()
        if watch:
            watch_directory = self.source_dir()
        else:
            watch_directory = None
        watch_callback=self.build
        utils.run_server(directory,access,port,watch_directory,watch_callback)

    def build(self):
        log.info(f"pretending to build target {self.name()}")

    def publish(self):
        if self.format() != "html":
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
        if not utils.directory_exists(self.output_dir()):
            log.error("The directory `{self.output_dir()}` does not exist. Maybe try `pretext build` first?")
            return
        log.info(f"Preparing to publish the latest build located in `{self.output_dir()}`.")
        docs_path = os.path.join(self.__project_path,"docs")
        shutil.rmtree(docs_path,ignore_errors=True)
        shutil.copytree(self.output_dir(),docs_path)
        log.info(f"Latest build copied to `{docs_path}`.")
        repo.git.add('docs')
        try:
            repo.git.commit(message=f"Publish latest build of target {self.name()}.")
        except git.exc.GitCommandError:
            log.error("Latest build is the same as last published build.")
            return
        log.info("Pushing to GitHub. (Your password may be required below.)")
        origin.push()
        log.info(f"Latest build successfully pushed to GitHub.")
        log.info("(It may take a few seconds for GitHub Pages to reflect any changes.)")


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
                targets_element.insert(target.xml_element)
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

