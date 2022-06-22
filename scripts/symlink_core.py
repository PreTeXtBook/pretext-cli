import sys, shutil
from pathlib import Path
import pretext.utils

def main(mathbook_path=Path("../pretext")):
    for subdir in ['xsl','schema','pretext']:
        original_path = (mathbook_path/subdir).resolve()
        link_path = Path('pretext')/'static'/subdir
        pretext.utils.remove_path(link_path)
        link_path.symlink_to(original_path)

    print(f"Linked local core pretext directory `{mathbook_path}`")

if __name__ == '__main__':
    try:
        mathbook_path = Path(sys.argv[1])
    except IndexError:
        mathbook_path = Path("../pretext")
    main(mathbook_path)