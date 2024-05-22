import sys
from pathlib import Path
from remove_path import remove_path
import pretext.core.resources


# This will redirect the static resources for pretext, including the core python script, xsl, css, etc to a local directory of your choosing that contains the clone of the pretext repository. This is useful for development purposes, as it allows you to make changes to the core python script and test with the CLI as you normally would.
def main(core_path: Path = Path("../pretext")) -> None:
    for subdir in ["xsl", "schema", "script", "css", "js", "js_lib"]:
        original_path = (core_path / subdir).resolve()
        link_path = pretext.core.resources.path(subdir)
        remove_path(link_path)
        link_path.symlink_to(original_path)
    original_path = (core_path / "pretext" / "pretext.py").resolve()
    link_path = Path("pretext") / "core" / "pretext.py"
    remove_path(link_path)
    link_path.symlink_to(original_path)

    print(f"Linked local core pretext directory `{core_path}`")


if __name__ == "__main__":
    try:
        core_path = Path(sys.argv[1])
    except IndexError:
        core_path = Path("../pretext")
    main(core_path)
