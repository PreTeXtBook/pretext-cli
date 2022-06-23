import sys, shutil
from pathlib import Path
from remove_path import remove_path

def main(mathbook_path=Path("../pretext")):
    for subdir in ['xsl','schema']:
        original_path = (mathbook_path/subdir).resolve()
        link_path = Path('pretext')/'static'/subdir
        remove_path(link_path)
        link_path.symlink_to(original_path)
    original_path = (mathbook_path/"pretext"/"pretext.py").resolve()
    link_path = Path('pretext')/'core'/"pretext.py"
    remove_path(link_path)
    link_path.symlink_to(original_path)

    print(f"Linked local core pretext directory `{mathbook_path}`")

if __name__ == '__main__':
    try:
        mathbook_path = Path(sys.argv[1])
    except IndexError:
        mathbook_path = Path("../pretext")
    main(mathbook_path)