import os
from pathlib import Path
import subprocess
import requests
import shutil
import tempfile
import zipfile

from pretext import CORE_COMMIT
import utils

import bundle_resources


def update_css(ptx_dir) -> None:
    print(f"current working directory: {os.getcwd()}")
    with utils.working_directory(ptx_dir / "script" / "cssbuilder"):
        print(f"current working directory: {os.getcwd()}")


def main() -> None:
    # grab copy of necessary PreTeXtBook/pretext files from specified commit

    print(f"Requesting core PreTeXtBook/pretext commit {CORE_COMMIT} from GitHub.")
    core_zip_path = Path("pretext").resolve() / "resources" / "core.zip"
    r = requests.get(
        f"https://github.com/PreTeXtBook/pretext/archive/{CORE_COMMIT}.zip"
    )
    # remove current core/pretext.py file in case it is a link
    utils.remove_path(Path("pretext").resolve() / "core" / "pretext.py")

    with open(core_zip_path, "wb") as f:
        f.write(r.content)
    with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:
        with zipfile.ZipFile(core_zip_path) as archive:
            archive.extractall(tmpdirname)
            # Run the cssbuilder script:
            script_dir = (
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "script" / "cssbuilder"
            )
            process_install = subprocess.run(
                ["npm", "install"],
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output, error = process_install.communicate()
            if process_install.returncode != 0:
                print(f"Error installing npm packages: {output, error}")
            process_build = subprocess.run(
                ["npm", "run", "build"],
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output, error = process_build.communicate()
            if process_build.returncode != 0:
                print(f"Error building CSS: {output, error}")
            # remove all the node_modules we used to build; we don't need anything in cssbuilder.
            shutil.rmtree(script_dir / "node_modules")
            print("Successfully built CSS.")
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
    bundle_resources.main()
    print("Successfully bundled core PreTeXtBook/pretext resources.")


if __name__ == "__main__":
    main()
