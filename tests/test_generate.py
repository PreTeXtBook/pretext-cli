"""
Tests to ensure that failed image generation is not reported as success.

When a core conversion function fails to produce an output file, the
individual_* functions in pretext/project/generate.py should raise an
exception so that the asset type is not added to the generated asset cache.
"""

import shutil
import typing as t
from pathlib import Path
from unittest.mock import patch

import pytest

from pretext.project import generate


def _make_asset_file(tmp_path: Path, name: str = "test_asset.tex") -> Path:
    """Create a minimal asset file in tmp_path for use in tests."""
    asset_file = tmp_path / name
    asset_file.write_text("some asset content")
    return asset_file


def test_individual_latex_image_raises_on_missing_output(tmp_path: Path) -> None:
    """individual_latex_image should raise when core does not produce the output file."""
    asset_file = _make_asset_file(tmp_path, "image.tex")
    cache_dir = tmp_path / "cache" / "latex-image"
    cache_dir.mkdir(parents=True)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    # Patch core so it does NOT create the output file.
    with patch("pretext.project.generate.core.individual_latex_image_conversion"):
        with pytest.raises(Exception, match="Failed to generate latex-image"):
            generate.individual_latex_image(
                latex_image=str(asset_file),
                outformat="svg",
                dest_dir=dest_dir,
                method="xelatex",
                cache_dir=tmp_path / "cache",
                skip_cache=True,
            )


def test_individual_latex_image_succeeds_when_output_exists(tmp_path: Path) -> None:
    """individual_latex_image should not raise when core produces the output file."""
    asset_file = _make_asset_file(tmp_path, "image.tex")
    cache_dir = tmp_path / "cache" / "latex-image"
    cache_dir.mkdir(parents=True)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    def fake_conversion(
        latex_image: str, outformat: str, dest_dir: Path, method: str
    ) -> None:
        # Simulate a successful conversion by creating the expected output file.
        (dest_dir / Path(latex_image).with_suffix(".svg").name).touch()

    with patch(
        "pretext.project.generate.core.individual_latex_image_conversion",
        side_effect=fake_conversion,
    ):
        # Should not raise.
        generate.individual_latex_image(
            latex_image=str(asset_file),
            outformat="svg",
            dest_dir=dest_dir,
            method="xelatex",
            cache_dir=tmp_path / "cache",
            skip_cache=True,
        )


def test_individual_asymptote_raises_on_missing_output(tmp_path: Path) -> None:
    """individual_asymptote should raise when core does not produce the output file."""
    asset_file = _make_asset_file(tmp_path, "diagram.asy")
    cache_dir = tmp_path / "cache" / "asymptote"
    cache_dir.mkdir(parents=True)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    with patch("pretext.project.generate.core.individual_asymptote_conversion"):
        with pytest.raises(Exception, match="Failed to generate asymptote diagram"):
            generate.individual_asymptote(
                asydiagram=str(asset_file),
                outformat="svg",
                method="server",
                asy_cli=[],
                asyversion="",
                alberta="",
                dest_dir=dest_dir,
                cache_dir=tmp_path / "cache",
                skip_cache=True,
            )


def test_individual_asymptote_succeeds_when_output_exists(tmp_path: Path) -> None:
    """individual_asymptote should not raise when core produces the output file."""
    asset_file = _make_asset_file(tmp_path, "diagram.asy")
    cache_dir = tmp_path / "cache" / "asymptote"
    cache_dir.mkdir(parents=True)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    def fake_conversion(
        asydiagram: str,
        outformat: str,
        method: str,
        asy_cli: list,
        asyversion: str,
        alberta: str,
        dest_dir: Path,
    ) -> None:
        (dest_dir / Path(asydiagram).with_suffix(".svg").name).touch()

    with patch(
        "pretext.project.generate.core.individual_asymptote_conversion",
        side_effect=fake_conversion,
    ):
        generate.individual_asymptote(
            asydiagram=str(asset_file),
            outformat="svg",
            method="server",
            asy_cli=[],
            asyversion="",
            alberta="",
            dest_dir=dest_dir,
            cache_dir=tmp_path / "cache",
            skip_cache=True,
        )


def test_individual_sage_raises_on_missing_output(tmp_path: Path) -> None:
    """individual_sage should raise when core does not produce the output file."""
    asset_file = _make_asset_file(tmp_path, "plot.sage")
    cache_dir = tmp_path / "cache" / "sageplot"
    cache_dir.mkdir(parents=True)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    with patch("pretext.project.generate.core.individual_sage_conversion"):
        with pytest.raises(Exception, match="Failed to generate sageplot diagram"):
            generate.individual_sage(
                sageplot=str(asset_file),
                outformat="svg",
                dest_dir=dest_dir,
                sage_executable_cmd=["sage"],
                cache_dir=tmp_path / "cache",
                skip_cache=True,
            )


def test_individual_sage_succeeds_when_output_exists(tmp_path: Path) -> None:
    """individual_sage should not raise when core produces the output file."""
    asset_file = _make_asset_file(tmp_path, "plot.sage")
    cache_dir = tmp_path / "cache" / "sageplot"
    cache_dir.mkdir(parents=True)
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    def fake_conversion(
        sageplot: str,
        outformat: str,
        dest_dir: Path,
        sage_executable_cmd: list,
    ) -> None:
        (dest_dir / Path(sageplot).with_suffix(".svg").name).touch()

    with patch(
        "pretext.project.generate.core.individual_sage_conversion",
        side_effect=fake_conversion,
    ):
        generate.individual_sage(
            sageplot=str(asset_file),
            outformat="svg",
            dest_dir=dest_dir,
            sage_executable_cmd=["sage"],
            cache_dir=tmp_path / "cache",
            skip_cache=True,
        )


def test_individual_prefigure_raises_on_missing_output(tmp_path: Path) -> None:
    """individual_prefigure should raise when core does not produce the output file."""
    asset_file = _make_asset_file(tmp_path, "figure.xml")
    cache_dir = tmp_path / "cache" / "prefigure"
    cache_dir.mkdir(parents=True)
    tmp_dir = tmp_path / "tmp_work"
    tmp_dir.mkdir()

    with patch("pretext.project.generate.core.individual_prefigure_conversion"):
        with pytest.raises(Exception, match="Failed to generate prefigure diagram"):
            generate.individual_prefigure(
                pfdiagram=str(asset_file),
                outformat="svg",
                tmp_dir=str(tmp_dir),
                cache_dir=tmp_path / "cache",
                skip_cache=True,
            )


def test_individual_prefigure_succeeds_when_output_exists(tmp_path: Path) -> None:
    """individual_prefigure should not raise when core produces the output file."""
    asset_file = _make_asset_file(tmp_path, "figure.xml")
    cache_dir = tmp_path / "cache" / "prefigure"
    cache_dir.mkdir(parents=True)
    tmp_dir = tmp_path / "tmp_work"
    tmp_dir.mkdir()

    def fake_conversion(pfdiagram: str, outformat: str) -> None:
        output_dir = tmp_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / Path(pfdiagram).with_suffix(".svg").name).touch()

    with patch(
        "pretext.project.generate.core.individual_prefigure_conversion",
        side_effect=fake_conversion,
    ):
        generate.individual_prefigure(
            pfdiagram=str(asset_file),
            outformat="svg",
            tmp_dir=str(tmp_dir),
            cache_dir=tmp_path / "cache",
            skip_cache=True,
        )


LIVE = "a" * 32
STALE = "b" * 32


@pytest.mark.parametrize(
    "name, expected",
    [
        (f"{LIVE}.svg", False),
        (f"{LIVE}.pdf", False),
        (f"{LIVE}-annotations.xml", False),
        (f"{STALE}.svg", True),
        (f"{STALE}-annotations.xml", True),
        (".DS_Store", False),
        ("my-image.svg", False),
        (f"{STALE}", False),
        (f"{STALE[:-1]}.svg", False),
        (f"{STALE}-other.svg", False),
    ],
)
def test_is_stale(name: str, expected: bool) -> None:
    """Only hash-named cache files whose hash is not live are stale."""
    assert generate.is_stale(Path(name), {LIVE}) is expected


def _populate_cache(cache_dir: Path) -> None:
    for name in [
        f"latex-image/{LIVE}.svg",
        f"latex-image/{LIVE}.eps",
        f"latex-image/{STALE}.svg",
        f"prefigure/{STALE}.svg",
        f"prefigure/{STALE}-annotations.xml",
        f"prefigure/tactile/{STALE}.pdf",
        "prefigure/notes.txt",
        f"journal/{STALE}.sty",
    ]:
        path = cache_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


def test_prune_cache_removes_only_stale_files(tmp_path: Path) -> None:
    """prune_cache removes stale hash-named files (including in subdirectories), keeps every format of live hashes, and ignores directories of non-asset caches."""
    _populate_cache(tmp_path)
    live = {"latex-image": {LIVE}, "prefigure": set()}
    removed = generate.prune_cache(tmp_path, live)
    assert {p.relative_to(tmp_path).as_posix() for p in removed} == {
        f"latex-image/{STALE}.svg",
        f"prefigure/{STALE}.svg",
        f"prefigure/{STALE}-annotations.xml",
        f"prefigure/tactile/{STALE}.pdf",
    }
    assert all(not p.exists() for p in removed)
    for kept in [
        f"latex-image/{LIVE}.svg",
        f"latex-image/{LIVE}.eps",
        "prefigure/notes.txt",
        f"journal/{STALE}.sty",
    ]:
        assert (tmp_path / kept).exists()


def test_prune_cache_dry_run_removes_nothing(tmp_path: Path) -> None:
    """With dry_run, prune_cache reports stale files but leaves them in place."""
    _populate_cache(tmp_path)
    removed = generate.prune_cache(
        tmp_path, {"latex-image": {LIVE}, "prefigure": set()}, dry_run=True
    )
    assert len(removed) == 4
    assert all(p.exists() for p in removed)


def _interrupted_copy(src: Path, dst: Path) -> None:
    """Simulate a copy that is killed partway through: write half the file, then interrupt."""
    data = Path(src).read_bytes()
    Path(dst).write_bytes(data[: len(data) // 2])
    raise KeyboardInterrupt


def test_copy_to_cache_writes_complete_file(tmp_path: Path) -> None:
    """copy_to_cache creates the cache file (and its directory) and leaves no temporary files."""
    output_file = tmp_path / "diagram.svg"
    output_file.write_text("<svg>complete</svg>")
    cache_file = tmp_path / "cache" / "asymptote" / f"{LIVE}.svg"
    generate.copy_to_cache(output_file, cache_file)
    assert cache_file.read_text() == "<svg>complete</svg>"
    assert list(cache_file.parent.iterdir()) == [cache_file]


def test_interrupted_copy_to_cache_leaves_no_cache_file(tmp_path: Path) -> None:
    """An interrupted copy never leaves a partial file under the cached name, nor a temporary file behind."""
    output_file = tmp_path / "diagram.svg"
    output_file.write_text("<svg>complete</svg>")
    cache_file = tmp_path / "cache" / f"{LIVE}.svg"
    with patch("pretext.project.generate.shutil.copy2", side_effect=_interrupted_copy):
        with pytest.raises(KeyboardInterrupt):
            generate.copy_to_cache(output_file, cache_file)
    assert not cache_file.exists()
    assert list(cache_file.parent.iterdir()) == []


def test_interrupted_copy_to_cache_keeps_existing_cache_file(tmp_path: Path) -> None:
    """An interrupted overwrite leaves the previous cache file intact."""
    output_file = tmp_path / "diagram.svg"
    output_file.write_text("<svg>new</svg>")
    cache_file = tmp_path / "cache" / f"{LIVE}.svg"
    cache_file.parent.mkdir()
    cache_file.write_text("<svg>old</svg>")
    with patch("pretext.project.generate.shutil.copy2", side_effect=_interrupted_copy):
        with pytest.raises(KeyboardInterrupt):
            generate.copy_to_cache(output_file, cache_file)
    assert cache_file.read_text() == "<svg>old</svg>"
    assert list(cache_file.parent.iterdir()) == [cache_file]


def test_interrupted_cache_copy_regenerates_on_next_build(tmp_path: Path) -> None:
    """If saving a generated asset to the cache is interrupted, the next build regenerates the asset instead of reusing a partial cache file."""
    asset_file = _make_asset_file(tmp_path, "diagram.asy")
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    (tmp_path / "cache" / "asymptote").mkdir(parents=True)
    calls = []

    def fake_conversion(
        asydiagram: str,
        outformat: str,
        method: str,
        asy_cli: list,
        asyversion: str,
        alberta: str,
        dest_dir: Path,
    ) -> None:
        calls.append(asydiagram)
        (dest_dir / Path(asydiagram).with_suffix(".svg").name).write_text(
            "<svg>complete</svg>"
        )

    def build() -> None:
        generate.individual_asymptote(
            asydiagram=str(asset_file),
            outformat="svg",
            method="server",
            asy_cli=[],
            asyversion="",
            alberta="",
            dest_dir=dest_dir,
            cache_dir=tmp_path / "cache",
        )

    with patch(
        "pretext.project.generate.core.individual_asymptote_conversion",
        side_effect=fake_conversion,
    ):
        with patch(
            "pretext.project.generate.shutil.copy2", side_effect=_interrupted_copy
        ):
            with pytest.raises(KeyboardInterrupt):
                build()
        build()
    assert len(calls) == 2
    cache_file = generate.cache_asset_filename(
        asset_file, "svg", tmp_path / "cache" / "asymptote"
    )
    assert cache_file.read_text() == "<svg>complete</svg>"


# ---------------------------------------------------------------------------
# WeBWorK: a cache entry is a directory holding the representations file and
# the problem's images.


def _write_representations(reps_file: Path, failure: t.Optional[str] = None) -> None:
    attribute = f' failure="{failure}"' if failure else ""
    reps_file.write_text(
        f'<webwork-reps assembly-id="{reps_file.stem}"><static seed="1"{attribute}/></webwork-reps>'
    )


def _fake_webwork_conversion(
    problem_file: str, dest_dir: str, abort_early: bool, renderer: t.Dict[str, t.Any]
) -> t.List[str]:
    """Simulates core: writes the representations file and one image, returning both."""
    problem_id = Path(problem_file).stem
    reps_file = Path(dest_dir) / f"{problem_id}.xml"
    image_file = Path(dest_dir) / "images" / f"{problem_id}-image-1.png"
    image_file.parent.mkdir(exist_ok=True)
    _write_representations(reps_file)
    image_file.write_bytes(b"png")
    return [str(reps_file), str(image_file)]


def _webwork_dirs(tmp_path: Path) -> t.Tuple[Path, Path, Path]:
    """The extracted problem file, the destination directory, and the cache directory."""
    problem_file = tmp_path / "extracted" / "ex-graph.xml"
    problem_file.parent.mkdir()
    problem_file.write_text("<ww-extraction><problem id='ex-graph'/></ww-extraction>")
    dest_dir = tmp_path / "generated" / "webwork"
    (dest_dir / "images").mkdir(parents=True)
    cache_dir = tmp_path / "cache"
    (cache_dir / "webwork").mkdir(parents=True)
    return problem_file, dest_dir, cache_dir


def test_individual_webwork_raises_on_missing_output(tmp_path: Path) -> None:
    """individual_webwork should raise when core does not write the representations file."""
    problem_file, dest_dir, cache_dir = _webwork_dirs(tmp_path)
    with patch(
        "pretext.project.generate.core.individual_webwork_conversion",
        return_value=[],
    ):
        with pytest.raises(Exception, match="Failed to generate representations"):
            generate.individual_webwork(
                str(problem_file), str(dest_dir), False, {}, cache_dir, skip_cache=True
            )


def test_individual_webwork_caches_every_written_file(tmp_path: Path) -> None:
    """The files core reports writing are copied into a hash-named cache directory, mirroring the destination layout."""
    problem_file, dest_dir, cache_dir = _webwork_dirs(tmp_path)
    with patch(
        "pretext.project.generate.core.individual_webwork_conversion",
        side_effect=_fake_webwork_conversion,
    ):
        generate.individual_webwork(
            str(problem_file), str(dest_dir), False, {}, cache_dir
        )
    cache_entry = cache_dir / "webwork" / generate.hash_asset_file(problem_file)
    assert (cache_entry / "ex-graph.xml").exists()
    assert (cache_entry / "images" / "ex-graph-image-1.png").exists()


def test_individual_webwork_uses_cache_without_calling_core(tmp_path: Path) -> None:
    """A second generation of an unchanged problem restores its files from the cache and never calls core."""
    problem_file, dest_dir, cache_dir = _webwork_dirs(tmp_path)
    with patch(
        "pretext.project.generate.core.individual_webwork_conversion",
        side_effect=_fake_webwork_conversion,
    ):
        generate.individual_webwork(
            str(problem_file), str(dest_dir), False, {}, cache_dir
        )
    shutil.rmtree(dest_dir)
    (dest_dir / "images").mkdir(parents=True)
    with patch(
        "pretext.project.generate.core.individual_webwork_conversion"
    ) as conversion:
        generate.individual_webwork(
            str(problem_file), str(dest_dir), False, {}, cache_dir
        )
        conversion.assert_not_called()
    assert (dest_dir / "ex-graph.xml").exists()
    assert (dest_dir / "images" / "ex-graph-image-1.png").read_bytes() == b"png"


def test_individual_webwork_skip_cache_regenerates(tmp_path: Path) -> None:
    """With skip_cache, core is called even though a cache entry exists, and the entry is replaced."""
    problem_file, dest_dir, cache_dir = _webwork_dirs(tmp_path)
    cache_entry = cache_dir / "webwork" / generate.hash_asset_file(problem_file)
    cache_entry.mkdir()
    (cache_entry / "ex-graph.xml").write_text("stale")
    (cache_entry / "images").mkdir()
    (cache_entry / "images" / "ex-graph-image-2.png").write_bytes(b"old")
    with patch(
        "pretext.project.generate.core.individual_webwork_conversion",
        side_effect=_fake_webwork_conversion,
    ) as conversion:
        generate.individual_webwork(
            str(problem_file), str(dest_dir), False, {}, cache_dir, skip_cache=True
        )
        conversion.assert_called_once()
    assert (cache_entry / "ex-graph.xml").read_text() != "stale"
    assert not (cache_entry / "images" / "ex-graph-image-2.png").exists()
    assert (cache_entry / "images" / "ex-graph-image-1.png").exists()


def test_individual_webwork_does_not_cache_failures(tmp_path: Path) -> None:
    """Representations recording a failure to render are written for the build but not cached."""
    problem_file, dest_dir, cache_dir = _webwork_dirs(tmp_path)

    def failed_conversion(
        problem_file: str,
        dest_dir: str,
        abort_early: bool,
        renderer: t.Dict[str, t.Any],
    ) -> t.List[str]:
        reps_file = Path(dest_dir) / f"{Path(problem_file).stem}.xml"
        _write_representations(reps_file, failure="compile")
        return [str(reps_file)]

    with patch(
        "pretext.project.generate.core.individual_webwork_conversion",
        side_effect=failed_conversion,
    ):
        generate.individual_webwork(
            str(problem_file), str(dest_dir), False, {}, cache_dir
        )
    assert (dest_dir / "ex-graph.xml").exists()
    assert not list((cache_dir / "webwork").iterdir())


def test_is_stale_directories(tmp_path: Path) -> None:
    """A hash-named directory is a cache entry; other directories are not."""
    for name in [LIVE, STALE, "images", "tactile"]:
        (tmp_path / name).mkdir()
    assert generate.is_stale(tmp_path / LIVE, {LIVE}) is False
    assert generate.is_stale(tmp_path / STALE, {LIVE}) is True
    assert generate.is_stale(tmp_path / "images", {LIVE}) is False
    assert generate.is_stale(tmp_path / "tactile", {LIVE}) is False


def test_prune_cache_removes_stale_webwork_directories(tmp_path: Path) -> None:
    """A stale webwork entry is removed whole, as one entry; a live one keeps all its files."""
    for name in [
        f"webwork/{LIVE}/ex-live.xml",
        f"webwork/{LIVE}/images/ex-live-image-1.png",
        f"webwork/{STALE}/ex-stale.xml",
        f"webwork/{STALE}/images/ex-stale-image-1.png",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    removed = generate.prune_cache(tmp_path, {"webwork": {LIVE}})
    assert removed == [tmp_path / "webwork" / STALE]
    assert not (tmp_path / "webwork" / STALE).exists()
    assert (tmp_path / "webwork" / LIVE / "images" / "ex-live-image-1.png").exists()


def test_interrupted_webwork_cache_copy_regenerates_on_next_build(
    tmp_path: Path,
) -> None:
    """If saving a problem's files to the cache is interrupted, the entry lacks its representations file, so the next generation calls core again instead of restoring a partial entry."""
    problem_file, dest_dir, cache_dir = _webwork_dirs(tmp_path)
    with patch(
        "pretext.project.generate.core.individual_webwork_conversion",
        side_effect=_fake_webwork_conversion,
    ) as conversion:
        # interrupt the second copy: the image is cached, the representations file is not
        real_copy2 = shutil.copy2
        copies: t.List[Path] = []

        def copy_then_interrupt(src: Path, dst: Path) -> None:
            copies.append(Path(src))
            if len(copies) == 2:
                _interrupted_copy(src, dst)
            real_copy2(src, dst)

        with patch(
            "pretext.project.generate.shutil.copy2", side_effect=copy_then_interrupt
        ):
            with pytest.raises(KeyboardInterrupt):
                generate.individual_webwork(
                    str(problem_file), str(dest_dir), False, {}, cache_dir
                )
        assert copies[1].name == "ex-graph.xml"
        generate.individual_webwork(
            str(problem_file), str(dest_dir), False, {}, cache_dir
        )
        assert conversion.call_count == 2
    cache_entry = cache_dir / "webwork" / generate.hash_asset_file(problem_file)
    assert (cache_entry / "ex-graph.xml").exists()
    assert (cache_entry / "images" / "ex-graph-image-1.png").exists()
