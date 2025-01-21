import logging
import hashlib
from pathlib import Path
import shutil
from .. import core


log = logging.getLogger("ptxlogger")


# The individual asset type generation functions


def individual_asymptote(
    asydiagram, outformat, method, asy_cli, asyversion, alberta, dest_dir, cache_dir
):
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the dest_dir and returns.  If it does not, calls the core.individual_asymptote_conversion function to generate the diagram in the correct outformat and then copies it to the dest_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be a file extension.
    """
    log.debug(f"Using the CLI's individual_asymptote function")
    asset_file = Path(asydiagram).resolve()
    cache_file = cache_asset_filename(
        asset_file, outformat, cache_dir
    )
    output_file = dest_dir / asset_file.with_suffix(f".{outformat}").name
    if cache_file.exists():
        log.debug(f"Copying cached asymptote diagram {cache_file} to {dest_dir}")
        shutil.copy(cache_file, output_file)
    else:
        core.individual_asymptote_conversion(
        asydiagram, outformat, method, asy_cli, asyversion, alberta, dest_dir
        )
        if output_file.exists():
            log.debug(f"Created asymptote diagram {output_file}; copying to cache as {cache_file}")
            shutil.copy(output_file, cache_file)
    log.debug(f"Finished individual_asymptote function")


def individual_sage(sageplot, outformat, dest_dir, sage_executable_cmd, cache_dir):
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the dest_dir and returns.  If it does not, calls the core.individual_asymptote_conversion function to generate the diagram in the correct outformat and then copies it to the dest_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be a file extension.
    """

    log.debug(f"Using the CLI's individual_sage function")
    asset_file = Path(sageplot).resolve()
    cache_file = cache_asset_filename(
        asset_file, outformat, cache_dir
    )
    output_file = dest_dir / asset_file.with_suffix(f".{outformat}").name
    if cache_file.exists():
        log.debug(f"Copying cached sageplot diagram {cache_file} to {dest_dir}")
        shutil.copy(cache_file, output_file)
    else:
        core.individual_sage_conversion(sageplot, outformat, dest_dir, sage_executable_cmd)
        if output_file.exists():
            log.debug(f"Created sageplot diagram {output_file}; copying to cache as {cache_file}")
            shutil.copy(output_file, cache_file)
    log.debug(f"Finished individual_sage function")
    pass


def individual_latex_image(latex_image, outformat, dest_dir, method, cache_dir):
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the dest_dir and returns.  If it does not, calls the core.individual_latex_image_conversion function to generate the diagram in the correct outformat and then copies it to the dest_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be 'all' or a file extension.
    """
    asset_file = Path(latex_image).resolve()
    outformats = ["png", "pdf", "svg", "eps"] if outformat == "all" else [outformat]
    cache_files = {
        ext: cache_asset_filename(asset_file, ext, cache_dir) for ext in outformats
    }
    output_files = {
        ext: dest_dir / asset_file.with_suffix(f".{ext}").name for ext in outformats
    }
    log.debug(f"Using the CLI's individual_latex function")
    core.individual_latex_image_conversion(latex_image, outformat, dest_dir, method)
    log.debug(f"Finished individual_latex function")
    pass


def cache_asset_filename(asset_file: Path, extension: str, cache_dir: Path) -> str:
    # hash the asset file
    asset_hash = hashlib.md5(asset_file.read_bytes()).hexdigest()
    # create the cache file name
    return cache_dir / f"{asset_hash}.{extension}"
