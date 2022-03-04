import os
import shutil
import sys


def remove(path):
    """param <path> could either be relative or absolute."""
    # https://stackoverflow.com/a/41789397
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        shutil.rmtree(path)  # remove dir and all contains


mathbook_path = sys.argv[1]
for subdir in ["xsl", "schema", "pretext"]:
    original_path = os.path.abspath(os.path.join(mathbook_path, subdir))
    link_path = os.path.join("pretext", "static", subdir)
    remove(link_path)
    os.symlink(original_path, link_path)

print("Linked local rbeezer/mathbook ")
