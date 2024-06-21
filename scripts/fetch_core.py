import os
from pathlib import Path
import requests
import shutil
import tempfile
import zipfile

from pretext import CORE_COMMIT


def main() -> None:
    # grab copy of necessary PreTeXtBook/pretext files from specified commit

    print(f"Requesting core PreTeXtBook/pretext commit {CORE_COMMIT} from GitHub.")
    core_zip_path = Path("pretext").resolve() / "resources" / "core.zip"
    r = requests.get(
        f"https://github.com/PreTeXtBook/pretext/archive/{CORE_COMMIT}.zip"
    )
    with open(core_zip_path, "wb") as f:
        f.write(r.content)
    with tempfile.TemporaryDirectory(prefix="pretext_") as tmpdirname:
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


if __name__ == "__main__":
    main()
