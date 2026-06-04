import sys
from pathlib import Path

import pretext.resources
from scripts import utils


# This will redirect the static resources for pretext, including the core python script, xsl, css, etc to a local directory of your choosing that contains the clone of the pretext repository. This is useful for development purposes, as it allows you to make changes to the core python script and test with the CLI as you normally would.
def main(core_path: Path = Path("../pretext")) -> None:
    # ensure resources are installed
    pretext.resources.install()
    core_path = core_path.resolve()
    link_path = pretext.resources.resource_base_path() / "core"
    # Remove the current link or directory
    utils.remove_path(link_path)
    # Create a symlink to the core directory
    link_path.symlink_to(core_path)

    source_core_lib_path = core_path / "pretext" / "lib"
    local_core_path = Path("pretext").resolve() / "core"
    for existing_file in utils.core_python_files(local_core_path):
        utils.remove_path(existing_file)
    for source_file in utils.core_python_files(source_core_lib_path):
        (local_core_path / source_file.name).symlink_to(source_file)
    print(f"Linked local core pretext directory `{core_path}`")


if __name__ == "__main__":
    try:
        core_path = Path(sys.argv[1])
    except IndexError:
        core_path = Path("../pretext")
    main(core_path)
