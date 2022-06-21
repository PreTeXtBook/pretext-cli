from lxml import etree as ET
import os, shutil
import logging
import tempfile
from . import static, utils, generate
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
                 xmlid_root=None,
                 project_path=None,
                 pdf_method=None):
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
        # set name and pdf-method attributes
        if name is not None:
            xml_element.set("name",name)
        if pdf_method is not None:
            xml_element.set("pdf-method",pdf_method)
        # set subelements with text nodes
        tag_pairs = [
            ("format",format),
            ("source",source),
            ("publication",publication),
            ("output-dir",output_dir),
            ("xsl",xsl_path),
            ("xmlid-root",xmlid_root),
        ]
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

    def pdf_method(self):
        pdf_method = self.xml_element().get("pdf-method")
        if pdf_method is not None:
            return pdf_method.strip()
        else:
            return "xelatex" # default

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

    def xmlid_root(self):
        ele = self.xml_element().find("xmlid-root")
        if ele is None:
            return None
        else:   
            return ele.text.strip()



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
        # prepre core PreTeXt pythons scripts
        self.init_ptxcore()

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

    def view(self,target_name,access,port,watch=False):
        target = self.target(target_name)
        directory = target.output_dir()
        if watch:
            watch_directory = target.source_dir()
        else:
            watch_directory = None
        if not utils.directory_exists(target.output_dir()):
            log.error(f"The directory `{target.output_dir()}` does not exist.")
            log.error(f"Run `pretext build {target}` to build your project before viewing.")
            return
        watch_callback=lambda:self.build(target_name)
        utils.run_server(directory,access,port,watch_directory,watch_callback)

    def build(self,target_name,clean=False):
        # Check for xml syntax errors and quit if xml invalid:
        if not self.xml_source_is_valid(target_name):
            return
        if not self.xml_publication_is_valid(target_name):
            return
        # Validate xml against schema; continue with warning if invalid:
        self.xml_schema_validate(target_name)
        # Ensure directories for assets and generated assets to avoid errors when building:
        target = self.target(target_name)
        os.makedirs(target.external_dir(), exist_ok=True)
        os.makedirs(target.generated_dir(), exist_ok=True)
        if clean:
            # refuse to clean if output is not a subdirectory of the working directory or contains source/publication
            if Path(self.__project_path) not in Path(target.output_dir()).parents:
                log.warning("Refusing to clean output directory that isn't a proper subdirectory of the project.")
            elif Path(target.output_dir()) in Path(os.path.join(target.source_dir(),"foo")).parents or \
                Path(target.output_dir()) in Path(os.path.join(target.publication_dir(),"foo")).parents:
                log.warning("Refusing to clean output directory that contains source or publication files.")
            # handle request to clean directory that does not exist
            elif not os.path.isdir(target.output_dir()):
                log.warning(f"Directory {target.output_dir()} already does not exist, nothing to clean.")
            else:
                log.warning(f"Destroying directory {target.output_dir()} to clean previously built files.")
                shutil.rmtree(target.output_dir())
        #if custom xsl, copy it into a temporary directory (different from the building temporary directory)
        custom_xsl = None
        with tempfile.TemporaryDirectory() as temp_xsl_dir:
            if target.xsl_path() is not None:
                log.info(f'Building with custom xsl {target.xsl_path()} specified in project.ptx')
                utils.copy_expanded_xsl(target.xsl_path(), temp_xsl_dir)
                custom_xsl = os.path.join(temp_xsl_dir, os.path.basename(target.xsl_path()))
            log.info(f"Preparing to build into {target.output_dir()}.")
            try:
                if (target.format()=='html' or target.format()=='html-zip'):
                    zipped = (target.format()=='html-zip')
                    builder.html(target.source(),target.publication(),target.output_dir(),target.stringparams(),custom_xsl,target.xmlid_root(),zipped)
                elif target.format()=='latex':
                    builder.latex(target.source(),target.publication(),target.output_dir(),target.stringparams(),custom_xsl)
                    # core script doesn't put a copy of images in output for latex builds, so we do it instead here
                    shutil.copytree(target.external_dir(),os.path.join(target.output_dir(),"external"),dirs_exist_ok=True)
                    shutil.copytree(target.generated_dir(),os.path.join(target.output_dir(),"generated"),dirs_exist_ok=True)
                elif target.format()=='pdf':
                    builder.pdf(target.source(),target.publication(),target.output_dir(),target.stringparams(),custom_xsl,target.pdf_method())
            except Exception as e:
                log.critical(
                    f"A fatal error has occurred:\n {e} \nFor more info, run pretext with `-v debug`")
                log.debug(f"Critical error info:\n****\n", exc_info=True)
                return
            # build was successful
            log.info(f"\nSuccess! Run `pretext view {target.name()}` to see the results.\n")
    
    def generate(self,target_name,asset_list=None,all_formats=False):
        if asset_list is None:
            asset_list = []
            gen_all = True
        else:
            gen_all = False
        target = self.target(target_name)
        os.makedirs(target.generated_dir(), exist_ok=True)
        #build targets:
        if gen_all or "webwork" in asset_list:
            webwork_output = os.path.join(target.generated_dir(),'webwork')
            generate.webwork(
                target.source(), target.publication(), webwork_output, target.stringparams()
            )
        if gen_all or "latex-image" in asset_list:
            generate.latex_image(
                target.source(), target.publication(), target.generated_dir(), target.stringparams(), 
                target.format(), target.xmlid_root(), target.pdf_method(), all_formats
            )
        if gen_all or "asymptote" in asset_list:
            generate.asymptote(
                target.source(), target.publication(), target.generated_dir(), target.stringparams(), 
                target.format(), target.xmlid_root(), all_formats
            )
        if gen_all or "sageplot" in asset_list:
            generate.sageplot(
                target.source(), target.publication(), target.generated_dir(), target.stringparams(), 
                target.format(), target.xmlid_root(), all_formats
            )
        if gen_all or "interactive" in asset_list:
            generate.interactive(
                target.source(), target.publication(), target.generated_dir(), target.stringparams(), 
                target.xmlid_root(),
            )
        if gen_all or "youtube" in asset_list:
            generate.youtube(
                target.source(), target.publication(), target.generated_dir(), target.stringparams(), 
                target.xmlid_root(),
            )
        if gen_all or "codelens" in asset_list:
            generate.codelens(
                target.source(), target.publication(), target.generated_dir(), target.stringparams(), 
                target.xmlid_root(),
            )

    def deploy(self,target_name,update_source):
        try:
            import git, ghp_import
        except ImportError:
            log.error("Git must be installed to use this feature, but couldn't be found.")
            log.error("Visit https://github.com/git-guides/install-git for assistance.")
            return
        target = self.target(target_name)
        if target.format() != "html":
            log.error("Only HTML format targets are supported.")
            return
        try:
            repo = git.Repo(self.__project_path)
        except git.exc.InvalidGitRepositoryError:
            log.info("Initializing project with Git.")
            repo = git.Repo.init(self.__project_path)
            try:
                repo.config_reader().get_value("user", "name")
                repo.config_reader().get_value("user", "email")
            except:
                log.info("Setting up name/email configuration for Git...")
                name = input("Type a name to use with Git: ")
                email = input("Type your GitHub email to use with Git: ")
                with repo.config_writer() as w:
                    w.set_value("user", "name", name)
                    w.set_value("user", "email", email)
            repo.git.add(all=True)
            repo.git.commit(message="Initial commit")
            repo.active_branch.rename("main")
            log.info("Successfully initialized new Git repository!")
            log.info("")
        log.info(f"Preparing to deploy from active `{repo.active_branch.name}` git branch.")
        log.info("")
        if repo.bare or repo.is_dirty() or len(repo.untracked_files)>0:
            log.info("Changes to project source since last commit detected.")
            if update_source:
                log.info("Add/committing these changes to local Git repository.")
                log.info("")
                repo.git.add(all=True)
                repo.git.commit(message="Update to PreTeXt project source.")
            else:
                log.error("Either add and commit these changes with Git, or run")
                log.error("`pretext deploy -u` to have these changes updated automatically.")
                return
        if not utils.directory_exists(target.output_dir()):
            log.error(f"No build for `{target.name()}` was found in the directory `{target.output_dir()}`.")
            log.error(f"Try running `pretext view {target.name()} -b` to build and preview your project first.")
            return
        log.info(f"Using latest build located in `{target.output_dir()}`.")
        log.info("")
        try:
            origin = repo.remotes.origin
        except AttributeError:
            log.warning("Remote GitHub repository is not yet configured.")
            log.info("")
            log.info("And if you haven't already, create a remote GitHub repository for this project at:")
            log.info("    https://github.com/new")
            log.info("(Do NOT check any \"initialize\" options.)")
            log.info("Then provide your GitHub info below:")
            log.info("")
            username = input("Your GitHub username (e.g. JaneDoe): ").strip()
            reponame = input("Your GitHub repo name (e.g. my-great-book-repo): ").strip()
            ssh_info = f"git@github.com:{username}/{reponame}.git"
            repo.create_remote("origin", url=ssh_info)
            origin = repo.remotes.origin
            log.info("")
        log.info(f"Commiting your latest build to the `gh-pages` branch.")
        log.info("")
        ghp_import.ghp_import(
            target.output_dir(), 
            mesg=f"Latest build of target {target.name()}.",
            nojekyll=True
        )
        log.info(f"Attempting to connect to remote repository at `{origin.url}`...")
        log.info("(Your SSH password may be required.)")
        log.info("")
        try:
            repo_user = origin.url.split(":")[1].split("/")[0]
            repo_name = origin.url.split(":")[1].split("/")[1][:-4]
            repo_url = f"https://github.com/{repo_user}/{repo_name}/"
            pages_url = f"https://{repo_user}.github.io/{repo_name}/"
        except:
            repo_url = f"(unable to find GitHub URL from {origin.url})"
            pages_url = f"(unable to find GitHub Pages URL from {origin.url})"
        try:
            origin.push(refspec=f"{repo.active_branch.name}:{repo.active_branch.name}")
            origin.push(refspec=f"gh-pages:gh-pages")
        except git.exc.GitCommandError:
            log.warning(f"There was an issue connecting to GitHub repository located at {repo_url}")
            log.info("")
            log.info("If you haven't already, configure SSH with GitHub by following instructions at:")
            log.info("    https://docs.github.com/en/authentication/connecting-to-github-with-ssh")
            log.info("Then try to deploy again.")
            log.info("")
            log.info(f"If `{origin.url}` doesn't match your GitHub repository,")
            log.info("use `git remote remove origin` on the command line then try to deploy again.")
            log.info("")
            log.error("Deploy was unsuccessful.")
            return
        log.info("")
        log.info("Latest build successfully pushed to GitHub!")
        log.info("")
        log.info("To enable GitHub Pages, visit")
        log.info(f"    {repo_url}settings/pages")
        log.info("selecting the `gh-pages` branch with the `/ (root)` folder.")
        log.info("")
        log.info("Visit")
        log.info(f"    {repo_url}actions/")
        log.info("to check on the status of your GitHub Pages deployment.")
        log.info("")
        log.info("Your built project will soon be available to the public at:")
        log.info(f"    {pages_url}")

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
