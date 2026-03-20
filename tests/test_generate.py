"""
Tests to ensure that failed image generation is not reported as success.

When a core conversion function fails to produce an output file, the
individual_* functions in pretext/project/generate.py should raise an
exception so that the asset type is not added to the generated asset cache.
"""
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

    def fake_conversion(latex_image: str, outformat: str, dest_dir: Path, method: str) -> None:
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
