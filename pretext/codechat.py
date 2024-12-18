# ***********************************************************
# codechat.py -- Compute mapping used by the CodeChat System
# ***********************************************************
# This function computes a mapping between source file names and the resulting HTML files built from them by PreTeXt. The `CodeChat System <https://codechat-system.readthedocs.io>`_ then uses this mapping to synchronize between a source file and its resulting rendered form.
#
#
# Imports
# =======
# These are listed in the order prescribed by `PEP 8
# <http://www.python.org/dev/peps/pep-0008/#imports>`_.
#
# Standard library
# ----------------
import collections  # defaultdict
import glob  # glob
import json  # dumps
from pathlib import Path
import sys  # platform
import urllib.parse  # urlparse
import urllib.request  # pathname2url

# Third-party imports
# -------------------
# We assume a previous call to ``xsltproc`` has already verified that lxml is installed.
import lxml.etree as ET  # noqa: N812
import lxml.ElementInclude

# Local application imports
# -------------------------
# None.


# Mapping
# =======
# Build a mapping between XML IDs and the resulting generated HTML files. The goal: map from source files to the resulting HTML files produced by the pretext build. The data structure is:
#
# .. code::
#   :number-lines:
#
#   path_to_xml_id: Dict[
#       # A path to the source file
#       str,
#       # A list of XML IDs in this source file which produce HTML files.
#       List[str]
#   ]
#
# This allows a single source file to produce multiple HTML files, as well as supporting a one-to-one relationship. The list captures the order of appearance of the XML IDs in the tree -- element 0 is the first XML ID, etc.
def map_path_to_xml_id(
    # A path to the root XML file in the pretext book being processed.
    xml: Path,
    # A path to the project directory, which (should) contain ``codechat_config.yaml``.
    project_path: Path,
    # A path to the destination or output directory. The resulting JSON file will be stored there.
    dest_dir: str,
) -> None:
    # Make insertions easy by specifying that newly-created entries in ``path_to_xml_id`` contain an empty list.
    path_to_xml_id = collections.defaultdict(list)

    # Normalize path separators to current OS.
    _xml = str(xml.resolve())

    # This follows the `Python recommendations <https://docs.python.org/3/library/sys.html#sys.platform>`_.
    is_win = sys.platform == "win32"

    # Look at all HTML files in the output directory. Store only their stem, since this is what an XML ID specifies. Note that all output files will have the same path prefix (the ``dest_dir`` and the same suffix (``.html``); the stem is the only unique part.
    html_files = set(
        Path(html_file).stem for html_file in glob.glob(dest_dir + "/*.html")
    )

    # lxml turns ``xml:id`` into the string below.
    xml_ns = "{http://www.w3.org/XML/1998/namespace}"
    xml_base_attrib = f"{xml_ns}base"
    xml_id_attrib = f"{xml_ns}id"

    # Define a loader which sets the ``xml:base`` of an xincluded element. While lxml `evidently used to do this in 2013 <https://stackoverflow.com/a/18158472/16038919>`_, a change eliminated this ability per some `discussion <https://mail.gnome.org/archives/xml/2014-April/msg00015.html>`_, which included a rejected patch fixing this problem. `Current source <https://github.com/GNOME/libxml2/blob/master/xinclude.c#L1689>`_ lacks this patch.
    #
    # Since there's few docs on this function, ignore the lack of types.
    def my_loader(href: str, parse: str, encoding: str = None, parser=None):  # type: ignore
        # Decode the URL-encoded filename for non-xml, on-disk data. See `lxml.ElementInclude._lxml_default_loader`.
        if parse != "xml" and "://" not in href:
            href = urllib.parse.unquote(href)
        ret = lxml.ElementInclude._lxml_default_loader(href, parse, encoding, parser)
        # The return value may not be an element.
        if isinstance(ret, ET._Element):
            ret.attrib[xml_base_attrib] = href
        return ret

    # Load the XML, performing xincludes using this loader.
    huge_parser = ET.XMLParser(huge_tree=True)
    src_tree = ET.parse(_xml, parser=huge_parser)
    lxml.ElementInclude.include(src_tree, loader=my_loader)

    # Walk though every element with an xml ID. Note: the type stubs don't have the ``iterfind`` method, hence the ignore in the next line.
    for elem in src_tree.iterfind(f".//*[@{xml_id_attrib}]"):  # type: ignore
        # Consider only elemets whose ID produced an HTML file. TODO: use a walrus operator after Python 3.7 is EOL.
        xml_id = elem.get(xml_id_attrib)
        if xml_id in html_files:
            # Store this discovered mapping between ID and output file.
            #
            # The `elem.base <https://lxml.de/api/lxml.etree._Element-class.html#base>`_ gives the URL of this file (which is correct due to the custom loader). Extract the path.
            up = urllib.parse.urlparse(elem.base)
            # If this isn't a ``file`` scheme (or an unspecified schema, which seems to default to a file), we're lost.
            assert up.scheme in ("file", "")
            path = up.path
            # On Windows, this produces ``path == "/C:/path/to/file.ptx"``. Remove the slash.
            if is_win:
                path = path[1:]
            # Decode the URL-encoded filename.
            path = urllib.parse.unquote(path)
            # Use ``resolve()`` to standardize capitalization on Windows.
            stdpath = Path(path).resolve()
            # Make this path relative to the project directory, to avoid writing potentially confidential information (username / local filesystem paths) to the mapping file, which might be published to the web. Do this in posix, to avoid platform-specific paths.
            relpath = stdpath.relative_to(project_path).as_posix()
            # Add this XML ID to others for this path.
            path_to_xml_id[str(relpath)].append(xml_id)

    # Save the result as a JSON file in the ``dest_dir``.
    (Path(dest_dir) / ".mapping.json").write_text(json.dumps(path_to_xml_id))
