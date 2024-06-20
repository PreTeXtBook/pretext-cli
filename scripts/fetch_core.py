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
    with open(core_zip_path, 'wb') as f:
        f.write(r.content)
    with tempfile.TemporaryDirectory(prefix="pretext_") as tmpdirname:
        with zipfile.ZipFile(core_zip_path) as archive:
            pretext_py = archive.extract(
                f"pretext-{CORE_COMMIT}/pretext/pretext.py",
                path=tmpdirname,
            )
            assert Path(pretext_py).exists()
        shutil.copyfile(Path(pretext_py), Path("pretext").resolve() / "core" / "pretext.py")
    print("Successfully updated core PreTeXtBook/pretext resources from GitHub.")


if __name__ == "__main__":
    main()
