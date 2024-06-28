import sys
from pathlib import Path
import pretext.resources
from scripts import utils


# This will redirect the static resources for pretext, including the core python script, xsl, css, etc to a local directory of your choosing that contains the clone of the pretext repository. This is useful for development purposes, as it allows you to make changes to the core python script and test with the CLI as you normally would.
def main(core_path: Path = Path("../pretext")) -> None:
    core_path = core_path.resolve()
    link_path = pretext.resources.resource_base_path() / "core"
    # Remove the current link or directory
    utils.remove_path(link_path)
    # Create a symlink to the core directory
    link_path.symlink_to(core_path)

    # Remove the current pretext/core/pretext.py file
    script_link_path = Path("pretext").resolve() / "core" / "pretext.py"
    script_core_path = core_path / "pretext" / "core" / "pretext.py"
    utils.remove_path(script_link_path)
    # Link to the local core python script
    script_link_path.symlink_to(script_core_path)
    print(f"Linked local core pretext directory `{core_path}`")


if __name__ == "__main__":
    try:
        core_path = Path(sys.argv[1])
    except IndexError:
        core_path = Path("../pretext")
    main(core_path)
