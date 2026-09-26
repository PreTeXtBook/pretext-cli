import typing as t
import logging
import hashlib
from pathlib import Path
import re
import shutil
import tempfile
from .. import core

log = logging.getLogger("ptxlogger")


# The individual asset type generation functions
def individual_prefigure(
    pfdiagram: str,
    outformat: str,
    tmp_dir: str,
    cache_dir: Path,
    skip_cache: bool = False,
) -> None:
    """
    Checks whether a cached version of the diagram in the correct outformat exists.  If it does, copies it to the tmp_dir and returns.  If it does not, calls the core.individual_prefigure_conversion function to generate the diagram in the correct outformat and then copies it to the tmp_dir.  In the latter case, also makes a copy to the cached version in the cache_dir.
    - outformat will be a file extension.
    """
    log.debug("Using the CLI's individual_prefigure function")
    asset_file = Path(pfdiagram).resolve()
    # Set output directory and create it if it doesn't exist
    output_dir = Path(tmp_dir).resolve() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    # Set cache directory
    cache_dir = cache_dir / "prefigure"
    outformats = ["tactile", "pdf", "png", "svg"] if outformat == "all" else [outformat]
    if "tactile" in outformats:
        (cache_dir / "tactile").mkdir(parents=True, exist_ok=True)
    for format in outformats:
        log.debug(f"Generating prefigure diagram in {format} format")
        if format == "tactile":
            tactile_cache_dir = cache_dir / "tactile"
            cache_file = cache_asset_filename(asset_file, "pdf", tactile_cache_dir)
            output_file = output_dir / "tactile" / asset_file.with_suffix(".pdf").name
        else:
            cache_file = cache_asset_filename(asset_file, format, cache_dir)
            output_file = output_dir / asset_file.with_suffix(f".{format}").name
            log.debug(
                f"cache_file: {cache_file} and output_file: {output_file}; asset_file: {asset_file}"
            )
        if format == "svg":
            # look for file with -annotations suffix
            annotations_cache_file = cache_file.with_suffix("").with_name(
                cache_file.stem + "-annotations.xml"
            )
            annotations_output_file = output_file.with_suffix("").with_name(
                output_file.stem + "-annotations.xml"
            )
            log.debug(
                f"cache_file: {cache_file} and annotations_cache_file: {annotations_cache_file}; asset_file: {asset_file}"
            )
        if cache_file.exists() and not skip_cache:
            log.debug(f"Copying cached prefigure diagram {cache_file} to {output_file}")
            shutil.copy2(cache_file, output_file)
            if format == "svg" and annotations_cache_file.exists():
                log.debug(
                    f"Copying cached prefigure diagram {annotations_cache_file} to {output_file}"
                )
                shutil.copy2(annotations_cache_file, annotations_output_file)
        else:
            core.individual_prefigure_conversion(pfdiagram, format)
            if output_file.exists():
                log.debug(
                    f"Created prefigure diagram {output_file}; saving a copy to cache as {cache_file}"
                )
                shutil.copy2(output_file, cache_file)
                if format == "svg" and annotations_output_file.exists():
                    log.debug(
                        f"Created prefigure diagram {annotations_output_file}; saving a copy to cache as {annotations_cache_file}"
                    )
                    shutil.copy2(annotations_output_file, annotations_cache_file)
            else:
                msg = f"Failed to generate prefigure diagram {Path(pfdiagram).name} in {format} format."
                log.error(msg)
                raise Exception(msg)
    log.debug("Finished individual_prefigure function")


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
    cache_dir = cache_dir / "asymptote"
    cache_file = cache_asset_filename(asset_file, outformat, cache_dir)
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
        else:
            msg = f"Failed to generate asymptote diagram {Path(asydiagram).name} in {outformat} format."
            log.error(msg)
            raise Exception(msg)
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
    cache_dir = cache_dir / "sageplot"
    cache_file = cache_asset_filename(
        asset_file,
        outformat,
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
        else:
            msg = f"Failed to generate sageplot diagram {Path(sageplot).name} in {outformat} format."
            log.error(msg)
            raise Exception(msg)
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
    cache_dir = cache_dir / "latex-image"
    cache_files = {
        ext: cache_asset_filename(asset_file, ext, cache_dir) for ext in outformats
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
            else:
                msg = f"Failed to generate latex-image {Path(latex_image).name} in {ext} format."
                log.error(msg)
                raise Exception(msg)
    log.debug("Finished individual_latex function")


def hash_asset_file(asset_file: Path) -> str:
    hash = hashlib.md5()
    # hash the asset file
    hash.update(asset_file.read_bytes())
    return hash.hexdigest()


def cache_asset_filename(asset_file: Path, extension: str, cache_dir: Path) -> Path:
    # create the cache file name
    return cache_dir / f"{hash_asset_file(asset_file)}.{extension}"


# Cached asset types, with the core extraction stylesheet that produces the source files whose hashes name the cached files.  Each entry is a list of extra stringparams to run the extraction with; sageplot extraction differs by output format, so it runs once per format.
CACHED_ASSET_EXTRACTIONS: t.Dict[str, t.Tuple[str, t.List[t.Dict[str, str]]]] = {
    "latex-image": ("extract-latex-image.xsl", [{}]),
    "asymptote": ("extract-asymptote.xsl", [{}]),
    "sageplot": (
        "extract-sageplot.xsl",
        [{"sageplot.fileformat": f} for f in ["pdf", "svg", "png", "html"]],
    ),
    "prefigure": ("extract-prefigure.xsl", [{}]),
}


# Names of cache files, as created by cache_asset_filename (plus prefigure's -annotations.xml companions): an md5 hex digest, an optional -annotations suffix, and an extension.
CACHE_FILENAME_PATTERN = re.compile(r"^([0-9a-f]{32})(?:-annotations)?\.[A-Za-z0-9]+$")


def extracted_asset_hashes(
    xml_source: Path, pub_file: Path, stringparams: t.Dict[str, str]
) -> t.Dict[str, t.Set[str]]:
    """
    Runs each extraction stylesheet (as core does before converting) and returns, for each cached asset type, the set of hashes of the extracted source files.  These are exactly the hashes the individual_* functions above would use to name cache files.
    """
    xsl_dir = Path(core.common.get_ptx_xsl_path())
    hashes: t.Dict[str, t.Set[str]] = {}
    for asset_type, (xsl, param_variants) in CACHED_ASSET_EXTRACTIONS.items():
        hashes[asset_type] = set()
        for extra_params in param_variants:
            params = {**stringparams, **extra_params, "publisher": pub_file.as_posix()}
            with tempfile.TemporaryDirectory() as tmp_dir:
                core.common.xsltproc(
                    (xsl_dir / xsl).as_posix(), xml_source, None, tmp_dir, params
                )
                for extracted in Path(tmp_dir).iterdir():
                    # prefigure writes a publication file alongside its diagrams
                    if extracted.is_file() and extracted.name != "pf_publication.xml":
                        hashes[asset_type].add(hash_asset_file(extracted))
    return hashes


def is_stale(cache_file: Path, live_hashes: t.Set[str]) -> bool:
    """
    Decides whether a file in one of the cached asset directories should be removed, given the hashes of the asset sources currently in the project.  Only files named by a hash (e.g. <hash>.svg or <hash>-annotations.xml) are candidates; anything else is left alone.  A live hash keeps all of its formats.
    """
    match = CACHE_FILENAME_PATTERN.match(cache_file.name)
    return match is not None and match.group(1) not in live_hashes


def prune_cache(
    cache_dir: Path, live_hashes: t.Dict[str, t.Set[str]], dry_run: bool = False
) -> t.List[Path]:
    """
    Removes cached asset files whose source no longer appears in the project.  Returns the list of removed (or, with dry_run, removable) files.
    """
    stale: t.List[Path] = []
    for asset_type, hashes in live_hashes.items():
        asset_cache_dir = cache_dir / asset_type
        if not asset_cache_dir.is_dir():
            continue
        # rglob to include subdirectories such as prefigure/tactile
        for cache_file in sorted(asset_cache_dir.rglob("*")):
            if cache_file.is_file() and is_stale(cache_file, hashes):
                stale.append(cache_file)
                if not dry_run:
                    cache_file.unlink()
    return stale
