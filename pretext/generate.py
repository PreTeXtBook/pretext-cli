from lxml import etree as ET
import os
import logging
from . import utils, core
from pathlib import Path
from typing import Dict, List, Optional

# Get access to logger
log = logging.getLogger("ptxlogger")

# generate latex-image assets


def latex_image(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    target_format: str,
    xmlid_root: Optional[str],
    pdf_method: str,
    all_formats: bool = False,
) -> None:
    # Dictionary of formats for images based on target
    formats: Dict[str, List[str]] = {
        "pdf": [],
        "latex": [],
        "html": ["svg"],
        "epub": ["svg"],
        "kindle": ["png"],
    }
    # set overwrite formats to all when appropriate
    if all_formats:
        formats[target_format] = ["all"]
    # We assume passed paths are absolute.
    # set images directory
    # parse source so we can check for latex-image.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(
            li := source_xml.xpath("/pretext/*[not(docinfo)]//latex-image"), List
        )
        and len(li) > 0
        and formats[target_format] != []
    ):
        image_output = (output / "latex-image").resolve()
        os.makedirs(image_output, exist_ok=True)
        log.info("Now generating latex-images\n\n")
        # Check for external requirements
        utils.check_asset_execs("latex-image", formats[target_format])
        # call pretext-core's latex image module:
        with utils.working_directory(Path()):
            for outformat in formats[target_format]:
                try:
                    core.latex_image_conversion(
                        xml_source=ptxfile,
                        pub_file=pub_file.as_posix(),
                        stringparams=params,
                        xmlid_root=xmlid_root,
                        dest_dir=image_output.as_posix(),
                        outformat=outformat,
                        method=pdf_method,
                    )
                except Exception as e:
                    log.error(e)
                    log.debug("Exception info:\n##################\n", exc_info=True)
                    log.info("##################")
                    log.error(
                        "Failed to generate some latex-image elements.  Check your source and partial output to diagnose the issue."
                    )
                    log.warning("Continuing...")
    else:
        log.info("Note: No latex-image elements found.")


# generate sageplot assets


def sageplot(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    target_format: str,
    xmlid_root: Optional[str],
    all_formats: bool = False,
) -> None:
    # Dictionary of formats for images based on target
    formats = {
        "pdf": ["pdf", "png"],
        "latex": ["pdf", "png"],
        "html": ["html", "svg"],
        "epub": ["svg"],
        "kindle": ["png"],
    }
    # set overwrite formats to all when appropriate
    if all_formats:
        formats[target_format] = ["all"]
    # We assume passed paths are absolute.
    # set images directory
    # parse source so we can check for sageplot.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(li := source_xml.xpath("/pretext/*[not(docinfo)]//sageplot"), List)
        and len(li) > 0
        and formats[target_format] is not None
    ):
        image_output = (output / "sageplot").resolve()
        os.makedirs(image_output, exist_ok=True)
        log.info("Now generating sageplot images\n\n")
        # Check for external requirements
        utils.check_asset_execs("sageplot", formats[target_format])
        with utils.working_directory(Path()):
            try:
                for outformat in formats[target_format]:
                    core.sage_conversion(
                        xml_source=ptxfile,
                        pub_file=pub_file.as_posix(),
                        stringparams=params,
                        xmlid_root=xmlid_root,
                        dest_dir=image_output.as_posix(),
                        outformat=outformat,
                    )
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error(
                    "Failed to generate some sageplot elements.  Check your source and partial output to diagnose the issue."
                )
                log.warning("Continuing...")
    else:
        log.info("Note: No sageplot elements found.")


# generate asymptote assets


def asymptote(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    target_format: str,
    xmlid_root: Optional[str],
    all_formats: bool = False,
) -> None:
    # Dictionary of formats for images based on target
    formats = {
        "pdf": ["pdf"],
        "latex": ["pdf"],
        "html": ["html"],
        "epub": ["svg"],
        "kindle": ["png"],
    }
    # set overwrite formats to all when appropriate
    if all_formats:
        formats[target_format] = ["all"]
    # We assume passed paths are absolute.
    # parse source so we can check for asymptote.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(li := source_xml.xpath("/pretext/*[not(docinfo)]//asymptote"), List)
        and len(li) > 0
        and formats[target_format] is not None
    ):
        image_output = (output / "asymptote").resolve()
        os.makedirs(image_output, exist_ok=True)
        log.info("Now generating asymptote images\n\n")
        with utils.working_directory(Path()):
            try:
                for outformat in formats[target_format]:
                    core.asymptote_conversion(
                        xml_source=ptxfile,
                        pub_file=pub_file.as_posix(),
                        stringparams=params,
                        xmlid_root=xmlid_root,
                        dest_dir=image_output.as_posix(),
                        outformat=outformat,
                        method="server",
                    )
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error(
                    "Failed to generate some asymptote elements. Check your source and partial output to diagnose the issue."
                )
                log.warning("Continuing...")
    else:
        log.info("Note: No asymptote elements found.")


# generate interactive preview assets


def interactive(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    xmlid_root: Optional[str],
) -> None:
    # We assume passed paths are absolute.
    # parse source so we can check for interactives.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(
            li := source_xml.xpath("/pretext/*[not(docinfo)]//interactive"), List
        )
        and len(li) > 0
    ):
        # First verify that playwright has dependencies installed:
        utils.playwright_install()
        image_output = (output / "preview").resolve()
        os.makedirs(image_output, exist_ok=True)
        log.info("Now generating preview images for interactives\n\n")
        with utils.working_directory(Path()):
            try:
                core.preview_images(
                    xml_source=ptxfile,
                    pub_file=pub_file.as_posix(),
                    stringparams=params,
                    xmlid_root=xmlid_root,
                    dest_dir=image_output.as_posix(),
                )
            except Exception as e:
                log.error(
                    "Failed to generate interactive element previews. Check debug log for info."
                )
                log.debug(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.warning("Continuing...")
    else:
        log.info("Note: No interactive elements found.")


# generate youtube thumbnail assets


def youtube(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    xmlid_root: Optional[str],
) -> None:
    # We assume passed paths are absolute.
    # parse source so we can check for videos.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(
            li := source_xml.xpath("/pretext/*[not(docinfo)]//video[@youtube]"), List
        )
        and len(li) > 0
    ):
        image_output = (output / "youtube").resolve()
        os.makedirs(image_output, exist_ok=True)
        log.info("Now generating youtube previews\n\n")
        with utils.working_directory(Path()):
            try:
                core.youtube_thumbnail(
                    xml_source=ptxfile,
                    pub_file=pub_file.as_posix(),
                    stringparams=params,
                    xmlid_root=xmlid_root,
                    dest_dir=image_output.as_posix(),
                )
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error(
                    "Failed to generate some youtube video previews. Check your source and partial output to diagnose the issue."
                )
                log.warning("Continuing...")
    else:
        log.info("Note: No video@youtube elements found.")


# generate webwork assets


def webwork(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    xmlid_root: Optional[str] = None,
) -> None:
    # We assume passed paths are absolute.
    # parse source so we can check for webwork.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if isinstance(li := source_xml.xpath("//webwork[node()|@*]"), List) and len(li) > 0:
        ww_output = (output / "webwork").resolve()
        os.makedirs(ww_output, exist_ok=True)
        log.info("Now generating webwork representation\n\n")
        with utils.working_directory(Path()):
            try:
                core.webwork_to_xml(
                    xml_source=ptxfile,
                    pub_file=pub_file.as_posix(),
                    stringparams=params,
                    xmlid_root=xmlid_root,
                    abort_early=True,
                    dest_dir=ww_output.as_posix(),
                    server_params=None,
                )
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error(
                    "Failed to generate the webwork-representations file.  Check your source and partial output to diagnose the issue."
                )
                log.warning("Continuing...")
    else:
        log.info("Note: No webwork elements found.")


# generate codelens trace assets


def codelens(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    xmlid_root: Optional[str],
) -> None:
    # We assume passed paths are absolute.
    # parse source so we can check for webwork.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(li := source_xml.xpath("//program[@interactive = 'codelens']"), List)
        and len(li) > 0
    ):
        trace_output = (output / "trace").resolve()
        os.makedirs(trace_output, exist_ok=True)
        log.info("Now generating codelens trace\n\n")
        with utils.working_directory(Path()):
            try:
                core.tracer(
                    xml_source=ptxfile,
                    pub_file=pub_file.as_posix(),
                    stringparams=params,
                    xmlid_root=xmlid_root,
                    dest_dir=trace_output.as_posix(),
                )
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error("Failed to generate codelens trace.")
                log.warning("Continuing...")
    else:
        log.info("Note: No program elements using codelens found.")


# generate qr code assets


def qrcodes(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    xmlid_root: Optional[str],
) -> None:
    # We assume passed paths are absolute.
    # parse source so we can check for videos.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(li1 := source_xml.xpath("/pretext/*[not(docinfo)]//video"), List)
        and len(li1) > 0
    ) or (
        isinstance(
            li2 := source_xml.xpath("/pretext/*[not(docinfo)]//interactive"), List
        )
        and len(li2) > 0
    ):
        image_output = (output / "qrcode").resolve()
        os.makedirs(image_output, exist_ok=True)
        log.info("Now generating QR codes for videos and/or interactives\n\n")
        with utils.working_directory(Path()):
            try:
                core.qrcode(
                    xml_source=ptxfile,
                    pub_file=pub_file.as_posix(),
                    stringparams=params,
                    xmlid_root=xmlid_root,
                    dest_dir=image_output.as_posix(),
                )
            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error(
                    "Failed to generate some QR codes for some videos or interactives. Check your source and partial output to diagnose the issue."
                )
                log.warning("Continuing...")
        # No else clause needed, since this isn't called specifically.


def play_button(output: Path) -> None:
    # Currently we do not parse source to look for videos, as this can run regardless of the source.
    image_output = (output / "play-button").resolve()
    os.makedirs(image_output, exist_ok=True)
    log.info("Now copying play-button image for videos\n\n")
    with utils.working_directory(Path()):
        try:
            core.play_button(dest_dir=image_output.as_posix())
        except Exception as e:
            log.error(e)
            log.debug("Exception info:\n##################\n", exc_info=True)
            log.info("##################")
            log.error(
                "Failed to copy play-button image for videos. Please report this on pretext-support."
            )
            log.warning("Continuing...")
    # No else clause needed, since this isn't called specifically.


# generate datafile assets
def datafiles(
    ptxfile: Path,
    pub_file: Path,
    output: Path,
    params: Dict[str, str],
    xmlid_root: Optional[str],
) -> None:
    # We assume passed paths are absolute.
    # parse source so we can check for datafile elements.
    source_xml = ET.parse(ptxfile)
    for _ in range(20):
        source_xml.xinclude()
    if (
        isinstance(li := source_xml.xpath("/pretext/*[not(docinfo)]//datafile"), List)
        and len(li) > 0
    ):
        datafile_output = (output / "datafile").resolve()
        os.makedirs(datafile_output, exist_ok=True)
        log.info("Now generating base64 versions of datafiles\n\n")
        with utils.working_directory(Path()):
            try:
                core.datafiles_to_xml(
                    xml_source=ptxfile,
                    pub_file=pub_file.as_posix(),
                    stringparams=params,
                    xmlid_root=xmlid_root,
                    dest_dir=datafile_output.as_posix(),
                )

            except Exception as e:
                log.error(e)
                log.debug("Exception info:\n##################\n", exc_info=True)
                log.info("##################")
                log.error(
                    "Failed to generate some datafile assets. Check your source and partial output to diagnose the issue."
                )
                log.warning("Continuing...")
    else:
        log.info("Note: No elements needing datafile conversion found")
