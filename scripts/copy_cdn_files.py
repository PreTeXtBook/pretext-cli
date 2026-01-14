import os
import sys
from pathlib import Path
import tarfile
import shutil
import tempfile
import zipfile

from pretext import CORE_COMMIT

import fetch_core


def main(args=None) -> None:
    if args:
        dist_path = Path(args[0]).resolve()
        print(f"Using dist location as: {args}")
    else:
        dist_path = Path("dist").resolve()

    static_dir = dist_path / "_static"
    # Make the _static directory inside dist_path if it doesn't exist
    if not static_dir.exists():
        os.makedirs(static_dir)

    # run fetch_core
    fetch_core.main()

    with tempfile.TemporaryDirectory(prefix="ptxcli_") as tmpdirname:
        # expand rs_services.zip
        with zipfile.ZipFile(
            Path("pretext").resolve() / "resources" / "rs_cache.zip", "r"
        ) as zip_ref:
            zip_ref.extractall(tmpdirname)
        # expand core.zip
        with zipfile.ZipFile(
            Path("pretext").resolve() / "resources" / "core.zip", "r"
        ) as zip_ref:
            zip_ref.extractall(tmpdirname)

        # Find dist-* file inside "rs_cache" directory
        rs_cache_dir = Path(tmpdirname)
        rs_cache_files = os.listdir(rs_cache_dir)
        rs_cache_files = [f for f in rs_cache_files if f.startswith("dist-")]
        if len(rs_cache_files) == 0:
            raise FileNotFoundError("No dist-* file found in rs_cache directory.")
        elif len(rs_cache_files) > 1:
            raise FileNotFoundError(
                "Multiple dist-* files found in rs_cache directory."
            )
        rs_cache_file = rs_cache_files[0]

        # expand tarfile and place in _static directory
        with tarfile.open(Path(tmpdirname) / rs_cache_file, "r") as tgz_ref:
            tgz_ref.extractall(static_dir, filter="fully_trusted")
        shutil.copy2(
            Path(tmpdirname) / "runestone_services.xml",
            static_dir / "runestone_services.xml",
        )

        # copy core files to _static directory
        shutil.copytree(
            Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "css" / "dist",
            static_dir / "pretext" / "css",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            Path(tmpdirname) / f"pretext-{CORE_COMMIT}" / "js",
            static_dir / "pretext" / "js",
            dirs_exist_ok=True,
        )


if __name__ == "__main__":
    main(sys.argv[1:])
