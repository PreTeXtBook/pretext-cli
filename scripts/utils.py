import shutil
from pathlib import Path


def remove_path(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink()  # remove the file
    elif path.is_dir():
        shutil.rmtree(path)  # remove dir and all it contains


def core_python_files(core_lib_path: Path) -> list[Path]:
    return sorted(
        path for path in core_lib_path.glob("*.py") if path.name != "__init__.py"
    )
