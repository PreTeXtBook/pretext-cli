import logging
import os
from pathlib import Path
import sys
from typing import Dict, Optional

from . import utils, core, codechat
from .project.xml import Executables

# Get access to logger
log = logging.getLogger("ptxlogger")


def build(
    format: str,
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    custom_xsl: Optional[Path],
    xmlid: Optional[str],
    zipped: bool = False,
    project_path: Optional[Path] = None,
    latex_engine: str = "xelatex",
    executables: Dict[str, str] = Executables().dict(),
    braille_mode: str = "emboss",
) -> None:
    core.set_executables(executables)
    try:
        if format == "html":
            html(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
                custom_xsl=custom_xsl,
                xmlid_root=xmlid,
                zipped=zipped,
                project_path=project_path,
            )
        elif format == "latex":
            latex(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
                custom_xsl=custom_xsl,
            )
        elif format == "pdf":
            pdf(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
                custom_xsl=custom_xsl,
                pdf_method=latex_engine,
            )
        elif format == "custom":
            if output.is_file():
                output_filename = output.name
                output = output.parent
            else:
                output_filename = None
            assert custom_xsl is not None
            custom(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
                custom_xsl=custom_xsl,
                output_filename=output_filename,
            )
        elif format == "epub":
            epub(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
            )
        elif format == "kindle":
            kindle(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
            )
        elif format == "braille":
            braille(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
                page_format=braille_mode,
            )
        elif format == "webwork":
            webwork_sets(
                ptxfile=ptxfile,
                pub_file=pub_file,
                output=output,
                stringparams=stringparams,
                zipped=zipped,
            )
        else:
            raise NotImplementedError(f"{format} is not supported")
    finally:
        core.release_temporary_directories()


def html(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    custom_xsl: Optional[Path],
    xmlid_root: Optional[str],
    zipped: bool = False,
    project_path: Optional[Path] = None,
) -> None:
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building HTML into {output}\n")
    if xmlid_root is not None:
        log.info(f"Only building @xml:id `{xmlid_root}`\n")
    if zipped:
        file_format = "zip"
    else:
        file_format = "html"
    # ensure working directory is preserved
    with utils.working_directory(Path()):
        try:
            core.html(
                ptxfile,
                pub_file.as_posix(),
                stringparams,
                xmlid_root,
                file_format,
                custom_xsl and custom_xsl.as_posix(),  # pass None or posix string
                None,
                output.as_posix(),
            )
            if project_path is None:
                project_path = utils.project_path(ptxfile)
            assert project_path is not None, f"Invalid project path to {ptxfile}."
            codechat.map_path_to_xml_id(ptxfile, project_path, output.as_posix())
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build html.  Exiting...")


def latex(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    custom_xsl: Optional[Path],
) -> None:
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    # ensure working directory is preserved
    with utils.working_directory(Path()):
        try:
            core.latex(
                ptxfile,
                pub_file.as_posix(),
                stringparams,
                custom_xsl and custom_xsl.as_posix(),  # pass None or posix string
                None,
                output.as_posix(),
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build latex.  Exiting...")


def pdf(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    custom_xsl: Optional[Path],
    pdf_method: str,
) -> None:
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building LaTeX into {output}\n")
    # ensure working directory is preserved
    with utils.working_directory(Path()):
        try:
            core.pdf(
                ptxfile,
                pub_file.as_posix(),
                stringparams,
                custom_xsl and custom_xsl.as_posix(),  # pass None or posix string
                None,
                dest_dir=output.as_posix(),
                method=pdf_method,
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build pdf.  Exiting...")


def custom(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    custom_xsl: Path,
    output_filename: Optional[str] = None,
) -> None:
    stringparams["publisher"] = pub_file.as_posix()
    os.makedirs(output, exist_ok=True)
    if output_filename is not None:
        output_filepath = output / output_filename
        output_dir = None
        log.info(f"\nNow building with custom {custom_xsl} into {output_filepath}\n")
    else:
        output_filepath = None
        output_dir = output
        log.info(f"\nNow building with custom {custom_xsl} into {output}\n")
    # ensure working directory is preserved
    with utils.working_directory(Path()):
        try:
            core.xsltproc(
                custom_xsl,
                ptxfile,
                output_filepath,
                output_dir=output_dir,
                stringparams=stringparams,
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed custom build.  Exiting...")


# build (non Kindle) ePub:
def epub(
    ptxfile: Path, pub_file: Path, output: Path, stringparams: Dict[str, str]
) -> None:
    os.makedirs(output, exist_ok=True)
    try:
        utils.npm_install()
    except Exception as e:
        log.debug(e)
        sys.exit(
            "Unable to build epub because node packages are not installed.  Exiting..."
        )
    log.info(f"\nNow building ePub into {output}\n")
    with utils.working_directory(Path()):
        try:
            core.epub(
                ptxfile,
                pub_file.as_posix(),
                out_file=None,  # will be derived from source
                dest_dir=output.as_posix(),
                math_format="svg",
                stringparams=stringparams,
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build epub.  Exiting...")


# build Kindle ePub:
def kindle(
    ptxfile: Path, pub_file: Path, output: Path, stringparams: Dict[str, str]
) -> None:
    os.makedirs(output, exist_ok=True)
    try:
        utils.npm_install()
    except Exception as e:
        log.critical(e)
        sys.exit(
            "Unable to build Kindle ePub because node packages are not installed.  Exiting..."
        )
    log.info(f"\nNow building Kindle ePub into {output}\n")
    with utils.working_directory(Path()):
        try:
            core.epub(
                ptxfile,
                pub_file.as_posix(),
                out_file=None,  # will be derived from source
                dest_dir=output.as_posix(),
                math_format="kindle",
                stringparams=stringparams,
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build kindle ebook.  Exiting...")


# build Braille:
def braille(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    page_format: str = "emboss",
) -> None:
    os.makedirs(output, exist_ok=True)
    log.warning(
        "Braille output is still experimental, and requires additional libraries from liblouis (specifically the file2brl software)."
    )
    try:
        utils.npm_install()
    except Exception as e:
        log.debug(e)
        sys.exit(
            "Unable to build braille because node packages could not be installed.  Exiting..."
        )
    log.info(f"\nNow building braille into {output}\n")
    with utils.working_directory(Path()):
        try:
            core.braille(
                xml_source=ptxfile,
                pub_file=pub_file.as_posix(),
                out_file=None,  # will be derived from source
                dest_dir=output.as_posix(),
                page_format=page_format,  # could be "eboss" or "electronic"
                stringparams=stringparams,
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build braille.  Exiting...")


# Build WeBWorK sets (for archive)
def webwork_sets(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    stringparams: Dict[str, str],
    zipped: bool = False,
) -> None:
    os.makedirs(output, exist_ok=True)
    log.info(f"\nNow building WeBWorK Sets into {output}\n")
    # ensure working directory is preserved
    with utils.working_directory(Path()):
        try:
            core.webwork_sets(
                xml_source=ptxfile,
                pub_file=pub_file.as_posix(),
                stringparams=stringparams,
                dest_dir=output.as_posix(),
                tgz=zipped,
            )
        except Exception as e:
            log.critical(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            sys.exit("Failed to build html.  Exiting...")
