import shutil
import sys
from pathlib import Path
import pretext.resources


# This will redirect the static resources for pretext, including the core python script, xsl, css, etc to a local directory of your choosing that contains the clone of the pretext repository. This is useful for development purposes, as it allows you to make changes to the core python script and test with the CLI as you normally would.
def main(core_path: Path = Path("../pretext")) -> None:
    core_path = core_path.resolve()
    link_path = pretext.resources.resource_base_path() / "core"
    if link_path.is_dir():
        shutil.rmtree(link_path)
    else:
        link_path.unlink()
    link_path.symlink_to(core_path)
    print(f"Linked local core pretext directory `{core_path}`")


if __name__ == "__main__":
    try:
        core_path = Path(sys.argv[1])
    except IndexError:
        core_path = Path("../pretext")
    main(core_path)
