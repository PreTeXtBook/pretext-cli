import requests, zipfile, io, shutil, tempfile, os
from pretext import CORE_COMMIT, utils
from pathlib import Path

def main():
    # grab copy of necessary PreTeXtBook/pretext files from specified commit

    print(f"Requesting core PreTeXtBook/pretext commit {CORE_COMMIT} from GitHub.")

    r = requests.get(f"https://github.com/PreTeXtBook/pretext/archive/{CORE_COMMIT}.zip")
    archive = zipfile.ZipFile(io.BytesIO(r.content))
    with tempfile.TemporaryDirectory() as tmpdirname:
        archive.extractall(tmpdirname)
        for subdir in ['xsl','pretext','schema']:
            utils.remove_path(Path("pretext")/"static"/subdir)
            shutil.copytree(
                Path(tmpdirname)/f"pretext-{CORE_COMMIT}"/subdir,
                Path("pretext")/"static"/subdir,
            )

    print("Successfully updated core PreTeXtBook/pretext resources from GitHub.")

if __name__ == '__main__':
    main()