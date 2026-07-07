"""
Unit tests for `pretext.codechat.map_path_to_xml_id`.

The CodeChat System uses this function to synchronize a PreTeXt source file
with the HTML file(s) built from it.  The function inspects the assembled
source (following xincludes), finds every element whose ``xml:id`` matches an
HTML file in the output directory, and writes a ``.mapping.json`` file of the
form ``{source-file-relative-path: [xml-ids-in-document-order]}``.

These tests build a tiny multi-file source tree by hand and fake the "built"
HTML output by touching empty files, so no actual `pretext build` is needed.
"""

import json
from pathlib import Path

from pretext import codechat


def _write_source(project: Path) -> Path:
    """Create a small book source split across two files via xinclude.

    Returns the path to the root source file.  The ``xml:id`` layout is:

    - ``main.ptx`` holds ``my-book`` and ``ch-inline``
    - ``ch-included.ptx`` holds ``ch-included`` and ``sec-included``
    """
    source = project / "source"
    source.mkdir(parents=True)
    (source / "main.ptx").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<pretext xmlns:xi="http://www.w3.org/2001/XInclude">\n'
        '  <book xml:id="my-book">\n'
        "    <title>Mapping test</title>\n"
        '    <chapter xml:id="ch-inline">\n'
        "      <title>Inline chapter</title>\n"
        "      <p>Text.</p>\n"
        "    </chapter>\n"
        '    <xi:include href="ch-included.ptx"/>\n'
        "  </book>\n"
        "</pretext>\n"
    )
    (source / "ch-included.ptx").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<chapter xml:id="ch-included">\n'
        "  <title>Included chapter</title>\n"
        '  <section xml:id="sec-included">\n'
        "    <title>Included section</title>\n"
        "    <p>More text.</p>\n"
        "  </section>\n"
        "</chapter>\n"
    )
    return source / "main.ptx"


def _fake_build(output: Path, xml_ids: list) -> None:
    """Simulate a built HTML target by touching one HTML file per xml:id."""
    output.mkdir(parents=True)
    for xml_id in xml_ids:
        (output / f"{xml_id}.html").touch()


def test_map_path_to_xml_id(tmp_path: Path) -> None:
    """Each source file maps to the xml:ids (in document order) that produced
    HTML output, with paths relative to the project and in posix form."""
    main = _write_source(tmp_path)
    output = tmp_path / "output"
    _fake_build(output, ["my-book", "ch-inline", "ch-included", "sec-included"])

    codechat.map_path_to_xml_id(main, tmp_path, str(output))

    mapping = json.loads((output / ".mapping.json").read_text())
    assert mapping == {
        "source/main.ptx": ["my-book", "ch-inline"],
        "source/ch-included.ptx": ["ch-included", "sec-included"],
    }


def test_map_path_to_xml_id_ignores_ids_without_html(tmp_path: Path) -> None:
    """xml:ids with no corresponding HTML file (e.g. ids that only produce
    knowls, or sections merged into a parent page) are left out of the map."""
    main = _write_source(tmp_path)
    output = tmp_path / "output"
    # Only the chapters produced pages; the book and section did not.
    _fake_build(output, ["ch-inline", "ch-included"])

    codechat.map_path_to_xml_id(main, tmp_path, str(output))

    mapping = json.loads((output / ".mapping.json").read_text())
    assert mapping == {
        "source/main.ptx": ["ch-inline"],
        "source/ch-included.ptx": ["ch-included"],
    }
