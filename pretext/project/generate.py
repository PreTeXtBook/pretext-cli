import typing as t
import logging
import hashlib
from pathlib import Path
import shutil
from .. import core


log = logging.getLogger("ptxlogger")


# The individual asset type generation functions


def individual_asymptote(
    asydiagram: str,
    outformat: str,
    method: str,
    asy_cli: t.List[str],
    asyversion: str,
    alberta: str,
    dest_dir: Path,
    cache_dir: Path,
    skip_cache: bool = False,
) -> None:
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the dest_dir and returns.  If it does not, calls the core.individual_asymptote_conversion function to generate the diagram in the correct outformat and then copies it to the dest_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be a file extension.
    """
    log.debug("Using the CLI's individual_asymptote function")
    asset_file = Path(asydiagram).resolve()
    cache_file = cache_asset_filename(asset_file, outformat, "asymptote", cache_dir)
    output_file = dest_dir / asset_file.with_suffix(f".{outformat}").name
    if cache_file.exists() and not skip_cache:
        log.debug(f"Copying cached asymptote diagram {cache_file} to {output_file}")
        shutil.copy2(cache_file, output_file)
    else:
        core.individual_asymptote_conversion(
            asydiagram, outformat, method, asy_cli, asyversion, alberta, dest_dir
        )
        if output_file.exists():
            log.debug(
                f"Created asymptote diagram {output_file}; saving a copy to cache as {cache_file}"
            )
            shutil.copy2(output_file, cache_file)
    log.debug("Finished individual_asymptote function")


def individual_sage(
    sageplot: str,
    outformat: str,
    dest_dir: Path,
    sage_executable_cmd: t.List[str],
    cache_dir: Path,
    skip_cache: bool = False,
) -> None:
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the dest_dir and returns.  If it does not, calls the core.individual_asymptote_conversion function to generate the diagram in the correct outformat and then copies it to the dest_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be a file extension.
    """

    log.debug("Using the CLI's individual_sage function")
    asset_file = Path(sageplot).resolve()
    cache_file = cache_asset_filename(
        asset_file,
        outformat,
        "sageplot",
        cache_dir,
    )
    output_file = dest_dir / asset_file.with_suffix(f".{outformat}").name
    if cache_file.exists() and not skip_cache:
        log.debug(f"Copying cached sageplot diagram {cache_file} to {output_file}")
        shutil.copy2(cache_file, output_file)
    else:
        core.individual_sage_conversion(
            sageplot, outformat, dest_dir, sage_executable_cmd
        )
        if output_file.exists():
            log.debug(
                f"Created sageplot diagram {output_file}; saving a copy to cache as {cache_file}"
            )
            shutil.copy2(output_file, cache_file)
    log.debug("Finished individual_sage function")


def individual_latex_image(
    latex_image: str,
    outformat: str,
    dest_dir: Path,
    method: str,
    cache_dir: Path,
    skip_cache: bool = False,
) -> None:
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the dest_dir and returns.  If it does not, calls the core.individual_latex_image_conversion function to generate the diagram in the correct outformat and then copies it to the dest_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be 'all' or a file extension.
    """
    log.debug("Using the CLI's individual_latex function")
    asset_file = Path(latex_image).resolve()
    outformats = ["png", "pdf", "svg", "eps"] if outformat == "all" else [outformat]
    cache_files = {
        ext: cache_asset_filename(asset_file, ext, "latex-image", cache_dir)
        for ext in outformats
    }
    output_files = {
        ext: dest_dir / asset_file.with_suffix(f".{ext}").name for ext in outformats
    }
    # In case outformat was "all", we check whether all the desired outformats are cached.  If not, we generate all of them (since it is only the first that is time-intensive)
    all_cached = True
    for ext in outformats:
        if not cache_files[ext].exists():
            all_cached = False
            break
    if all_cached and not skip_cache:
        for ext in outformats:
            log.debug(
                f"Copying cached latex-image {cache_files[ext]} to {output_files[ext]}"
            )
            shutil.copy2(cache_files[ext], output_files[ext])
    else:
        core.individual_latex_image_conversion(latex_image, outformat, dest_dir, method)
        for ext in outformats:
            if output_files[ext].exists():
                log.debug(
                    f"Created latex-image {output_files[ext]}; saving a copy to cache as {cache_files[ext]}"
                )
                shutil.copy2(output_files[ext], cache_files[ext])
    log.debug("Finished individual_latex function")


def cache_asset_filename(
    asset_file: Path, extension: str, asset_type: str, cache_dir: Path
) -> Path:
    asset_content = asset_file.read_bytes()
    hash = hashlib.md5()
    # hash the asset file
    hash.update(asset_content)
    asset_hash = hash.hexdigest()
    # create the cache file name
    return cache_dir / asset_type / f"{asset_hash}.{extension}"
