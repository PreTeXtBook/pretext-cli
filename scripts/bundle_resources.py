import shutil
from pathlib import Path


def main() -> None:
    shutil.make_archive(str(Path("pretext") / "resources" / "templates"), 'zip', Path("templates"))
    print("Templates successfully zipped.")
    # TODO: incorporate in pelican branch
    # shutil.make_archive(str(Path("pretext") / "resources" / "pelican"), 'zip', Path("pelican"))
    # print("Pelican resources successfully zipped.")


if __name__ == "__main__":
    main()
