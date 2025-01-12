import os
from pathlib import Path
import requests
import shutil
import tempfile
import zipfile

from pretext import CORE_COMMIT
import utils
import lxml.etree as ET

import bundle_resources


def main() -> None:
    # grab copy of necessary PreTeXtBook/pretext files from specified commit

    print(f"Requesting core PreTeXtBook/pretext commit {CORE_COMMIT} from GitHub.")
    core_zip_path = Path("pretext").resolve() / "resources" / "core.zip"
    core_zip = requests.get(
        f"https://github.com/PreTeXtBook/pretext/archive/{CORE_COMMIT}.zip", timeout=20
    )
    # remove current core/pretext.py file in case it is a link
    utils.remove_path(Path("pretext").resolve() / "core" / "pretext.py")

    with open(core_zip_path, "wb") as f:
        f.write(core_zip.content)

    # Get runestone services file:
    rs_services_path = Path("pretext").resolve() / "resources" / "runestone_services.xml"
    rs_services_file = requests.get("https://runestone.academy/cdn/runestone/latest/webpack_static_imports.xml", timeout=10)

    with open(rs_services_path, "wb") as f:
        f.write(rs_services_file.content)
        services = ET.fromstring(rs_services_file.content)
        # Interrogate the services XML
        rs_cdn_url = services.xpath("/all/cdn-url")[0].text
    # single Runestone Services version
        rs_version = services.xpath("/all/version")[0].text

    # Get the rs_services tgz file
    services_file_name = "dist-{}.tgz".format(rs_version)
    rs_services_tgz_path = Path("pretext").resolve() / "resources" / services_file_name
    rs_services_tgz = requests.get(rs_cdn_url + services_file_name, timeout=10)
    with open(rs_services_tgz_path, "wb") as f:
        f.write(rs_services_tgz.content)

    with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:
        with zipfile.ZipFile(core_zip_path) as archive:
            archive.extractall(tmpdirname)
            shutil.copyfile(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "pretext" / "pretext.py",
                Path("pretext").resolve() / "core" / "pretext.py",
            )
            shutil.copytree(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "examples",
                Path("tests").resolve() / "examples" / "core" / "examples",
                dirs_exist_ok=True,
            )
            shutil.rmtree(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "examples",
            )
            shutil.copytree(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "doc",
                Path("tests").resolve() / "examples" / "core" / "doc",
                dirs_exist_ok=True,
            )
            shutil.rmtree(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "doc",
            )
            with zipfile.ZipFile(
                Path("pretext").resolve() / "resources" / "core.zip",
                "w",
                zipfile.ZIP_DEFLATED,
            ) as zip_ref:
                for folder_name, _, filenames in os.walk(tmpdirname):
                    for filename in filenames:
                        file_path = Path(folder_name) / filename
                        zip_ref.write(
                            file_path, arcname=os.path.relpath(file_path, tmpdirname)
                        )
    print("Successfully updated core PreTeXtBook/pretext resources from GitHub.")
    bundle_resources.main()
    print("Successfully bundled core PreTeXtBook/pretext resources.")


if __name__ == "__main__":
    main()
