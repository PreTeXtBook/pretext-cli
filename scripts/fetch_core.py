import os
import sys
from pathlib import Path
import requests
import shutil
import tempfile
import zipfile

from pretext import CORE_COMMIT
import utils
import lxml.etree as ET  # noqa: N812

import bundle_resources


def get_runestone_services() -> None:
    # work in temporary directory:
    with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:

        # download runestone files to temporary directory:

        # Get runestone services file:
        rs_services_path = Path(tmpdirname) / "runestone_services.xml"
        rs_services_file = requests.get(
            "https://runestone.academy/cdn/runestone/latest/webpack_static_imports.xml",
            timeout=10,
        )

        with open(rs_services_path, "wb") as f:
            f.write(rs_services_file.content)
            services = ET.fromstring(rs_services_file.content)
            # Interrogate the services XML
            rs_cdn_url = services.xpath("/all/cdn-url")[0].text
            # single Runestone Services version
            rs_version = services.xpath("/all/version")[0].text

        # Get the rs_services tgz file
        services_file_name = "dist-{}.tgz".format(rs_version)
        rs_services_tgz_path = Path(tmpdirname) / services_file_name
        rs_services_tgz = requests.get(rs_cdn_url + services_file_name, timeout=10)
        with open(rs_services_tgz_path, "wb") as f:
            f.write(rs_services_tgz.content)

        # Now zip these two files and put them in the resources directory
        with zipfile.ZipFile(
            Path("pretext").resolve() / "resources" / "rs_cache.zip",
            "w",
            zipfile.ZIP_DEFLATED,
        ) as zip_ref:
            zip_ref.write(rs_services_path, arcname="runestone_services.xml")
            zip_ref.write(rs_services_tgz_path, arcname=services_file_name)


def main(args=None) -> None:
    print(args)
    if args:
        print(f"Arguments: {args}")
        repo_name = args[0]
    else:
        repo_name = "PreTeXtBook/pretext"

    # grab copy of necessary PreTeXtBook/pretext files from specified commit
    print(f"Requesting core {repo_name} commit {CORE_COMMIT} from GitHub.")
    core_zip_path = Path("pretext").resolve() / "resources" / "core.zip"
    core_zip = requests.get(f"https://github.com/{repo_name}/archive/{CORE_COMMIT}.zip")
    # remove current core/pretext.py file in case it is a link
    utils.remove_path(Path("pretext").resolve() / "core" / "pretext.py")

    with open(core_zip_path, "wb") as f:
        f.write(core_zip.content)

    with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:
        with zipfile.ZipFile(core_zip_path) as archive:
            archive.extractall(tmpdirname)
            # Run the cssbuilder script:
            # update_css(tmpdirname)

            shutil.copyfile(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "pretext" / "pretext.py",
                Path("pretext").resolve() / "core" / "pretext.py",
            )
            shutil.copyfile(
                Path(tmpdirname)
                / f"pretext-{CORE_COMMIT}"
                / "pretext"
                / "braille_format.py",
                Path("pretext").resolve() / "core" / "braille_format.py",
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
            print(
                "Successfully updated core PreTeXtBook/pretext files from GitHub.\n Now zippping core resources."
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

    # Get Runestone services file
    get_runestone_services()

    bundle_resources.main()
    print("Successfully bundled core PreTeXtBook/pretext resources.")


if __name__ == "__main__":
    main(sys.argv[1:])
