import shutil
from pathlib import Path


def remove_path(path: Path):
    if path.is_file() or path.is_symlink():
        path.unlink()  # remove the file
    elif path.is_dir():
        shutil.rmtree(path)  # remove dir and all it contains
