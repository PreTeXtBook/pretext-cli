import sys
import os
import re


# Simple utility for finding all pretext elements (tags) in an inputed project and reporting their frequency
def main(project_path) -> None:
    tag_counts = {}

    # Walk through the directory and subdirectories
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith((".xml", ".ptx")) and not file.startswith("."):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Count tags in the file
                        for line in content.splitlines():
                            line = line.strip()
                            tags = re.findall(r"<([\w\-]+)", line)
                            for tag in tags:
                                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")

    # Print the tag counts
    for tag, count in sorted(
        tag_counts.items(), key=lambda item: item[1], reverse=True
    ):
        print(f"{tag}: {count}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tag_counter.py <file_path>")
        sys.exit(1)
    file_path = sys.argv[1]
    main(file_path)
