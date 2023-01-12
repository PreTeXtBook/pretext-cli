import requests
import zipfile
import io
import shutil
import tempfile
from pretext import CORE_COMMIT
from pathlib import Path
from remove_path import remove_path


def main():
    # grab copy of necessary PreTeXtBook/pretext files from specified commit

    print(f"Requesting core PreTeXtBook/pretext commit {CORE_COMMIT} from GitHub.")
    pretext_dir = Path("pretext").resolve()
    r = requests.get(
        f"https://github.com/PreTeXtBook/pretext/archive/{CORE_COMMIT}.zip"
    )
    archive = zipfile.ZipFile(io.BytesIO(r.content))
    with tempfile.TemporaryDirectory() as tmpdirname:
        archive.extractall(tmpdirname)
        print("Creating zip of static folders")
        # Copy required folders to a single folder to be zipped:
        for subdir in ["xsl", "schema", "script", "css"]:
            shutil.copytree(
                Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / subdir,
                Path(tmpdirname) / "static" / subdir,
            )
        shutil.make_archive(
            "pretext/core/resources", "zip", Path(tmpdirname) / "static"
        )
        print("Copying new version of pretext.py to core directory")
        remove_path(pretext_dir / "core" / "pretext.py")
        shutil.copyfile(
            Path(tmpdirname).resolve()
            / f"pretext-{CORE_COMMIT}"
            / "pretext"
            / "pretext.py",
            Path("pretext") / "core" / "pretext.py",
        )

    print("Successfully updated core PreTeXtBook/pretext resources from GitHub.")


if __name__ == "__main__":
    main()
