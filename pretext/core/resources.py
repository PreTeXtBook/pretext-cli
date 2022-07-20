from pathlib import Path
import zipfile, importlib.resources
from .. import CORE_COMMIT

def path(*args) -> Path:
    # Checks that the local static path ~/.ptx/ contains the static files needed for core, and installs them if they are missing (or if the version is different from the installed version of pretext).  Then returns the absolute path to the static files (appending arguments)
    local_base_path = Path.home()/'.ptx'
    local_commit_file = Path(local_base_path)/".commit"
    if not Path.is_file(local_commit_file):
        print("Static pretext files do not appear to be installed.  Installing now.")
        install(local_base_path)
    # check that the static core_commit matches current core_commit
    with open(local_commit_file, "r") as f:
        static_commit = f.readline().strip()
    if static_commit != CORE_COMMIT:
        print("Static pretext files are out of date.  Installing them now.")
        install(local_base_path)
    return local_base_path.joinpath(*args)

def install(local_base_path):
    with importlib.resources.path("pretext.core","resources.zip") as static_zip:
        with zipfile.ZipFile(static_zip,"r") as zip:
            zip.extractall(local_base_path)
    # Write the current commit to local file
    with open(local_base_path/".commit","w") as f:
        f.write(CORE_COMMIT)
    print(f"Static files required for pretext have now been installed to {local_base_path}")
    return