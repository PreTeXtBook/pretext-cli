import logging
from .. import core


log = logging.getLogger("ptxlogger")


# The individual asset type generation functions


def individual_asymptote(asydiagram, outform, method, asy_cli, asyversion, alberta, dest_dir):
    log.warning(f"Using the CLI's individual_asymptote function")
    core.individual_asymptote_conversion(asydiagram, outform, method, asy_cli, asyversion, alberta, dest_dir)
    log.debug(f"Finished individual_asymptote function")
    pass


def individual_sage(sageplot, outformat, dest_dir, sage_executable_cmd):
    log.warning(f"Using the CLI's individual_sage function")
    core.individual_sage_conversion(sageplot, outformat, dest_dir, sage_executable_cmd)
    log.debug(f"Finished individual_sage function")
    pass


def individual_latex_image(latex_image, outformat, dest_dir, method):
    log.warning(f"Using the CLI's individual_latex function")
    core.individual_latex_image_conversion(latex_image, outformat, dest_dir, method)
    log.debug(f"Finished individual_latex function")
    pass