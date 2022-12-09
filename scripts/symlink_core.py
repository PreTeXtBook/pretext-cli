import sys
import shutil
from pathlib import Path
from remove_path import remove_path
import pretext.core.resources


def main(core_path: Path = Path("../pretext")):
    for subdir in ['xsl', 'schema', 'script', 'css']:
        original_path = (core_path/subdir).resolve()
        link_path = pretext.core.resources.path(subdir)
        remove_path(link_path)
        link_path.symlink_to(original_path)
    original_path = (core_path/"pretext"/"pretext.py").resolve()
    link_path = Path('pretext')/'core'/"pretext.py"
    remove_path(link_path)
    link_path.symlink_to(original_path)

    print(f"Linked local core pretext directory `{core_path}`")


if __name__ == '__main__':
    try:
        core_path = Path(sys.argv[1])
    except IndexError:
        core_path = Path("../pretext")
    main(core_path)
