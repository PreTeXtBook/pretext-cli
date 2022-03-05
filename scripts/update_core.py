import io
import os
import requests
import shutil
import tempfile
import zipfile


def remove(path):
    """param <path> could either be relative or absolute."""
    # https://stackoverflow.com/a/41789397
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains


# grab copy of necessary rbeezer/mathbook files from specified commit
with open("pretext/static/CORE_COMMIT", "r") as commitfile:
    commit = commitfile.readline().strip()

print(f"Requesting core PreTeXtBook/pretext commit {commit} from GitHub.")

r = requests.get(f"https://github.com/PreTeXtBook/pretext/archive/{commit}.zip")
archive = zipfile.ZipFile(io.BytesIO(r.content))
with tempfile.TemporaryDirectory() as tmpdirname:
    archive.extractall(tmpdirname)
    for subdir in ["xsl", "pretext", "schema"]:
        remove(os.path.join("pretext", "static", subdir))
        shutil.copytree(
            os.path.join(tmpdirname, f"pretext-{commit}", subdir),
            os.path.join("pretext", "static", subdir),
        )

print("Successfully updated core PreTeXtBook/pretext resources from GitHub.")
