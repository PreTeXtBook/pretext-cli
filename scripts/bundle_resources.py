import hashlib
import shutil
import re
import json
from pathlib import Path
from pretext import VERSION
from pretext.constants import PROJECT_RESOURCES


def main() -> None:
    # Load current hash table
    if (Path("pretext") / "resources" / "resource_hash_table.json").exists():
        with open(Path("pretext") / "resources" / "resource_hash_table.json", "r") as f:
            saved_hash_table = json.load(f)
        print(
            f"Loaded hash table from {Path('pretext') / 'resources' / 'resource_hash_table.json'}"
        )
    else:
        saved_hash_table = {}
    # Set up a dictionary for the hash of this version's files:
    resource_hash_table = {}
    # Update version generation dates in project resources
    for resource in PROJECT_RESOURCES:
        if resource == "requirements.txt":
            # Special case: requirements.txt is not a template
            continue
        with open(Path("templates") / resource, "r") as f:
            lines = f.readlines()
        with open(Path("templates") / resource, "w") as f:
            for line in lines:
                if "This file was automatically generated" in line:
                    # replace the version number with {VERSION}:
                    new_line = re.sub(
                        r"PreTeXt \d+\.\d+\.\d+", f"PreTeXt {VERSION}", line
                    )
                    f.write(new_line)
                else:
                    f.write(line)
        # Now hash the updated file to add to a hash-table for this version
        with open(Path("templates") / resource, "rb") as f:
            # Create SHA256 hash of file contents
            sha256_hash = hashlib.sha256()
            # Read the file and update the hash
            sha256_hash.update(f.read())
            resource_hash_table[resource] = sha256_hash.hexdigest()

    # Finally update the hash table and save it
    saved_hash_table[VERSION] = resource_hash_table
    with open(Path("pretext") / "resources" / "resource_hash_table.json", "w") as f:
        json.dump(saved_hash_table, f)
    print(
        f"Hash table saved to {Path('pretext') / 'resources' / 'resource_hash_table.json'}"
    )

    # Zip the templates and pelican resources
    shutil.make_archive(
        str(Path("pretext") / "resources" / "templates"), "zip", Path("templates")
    )
    print("Templates successfully zipped.")
    shutil.make_archive(
        str(Path("pretext") / "resources" / "pelican"), "zip", Path("pelican")
    )
    print("Pelican resources successfully zipped.")


if __name__ == "__main__":
    main()
