from datetime import date
from pathlib import Path


from pretext import CORE_COMMIT
from pretext import VERSION


def main() -> None:
    insert_lines = [
        "\n",
        f"## [{VERSION}] - {date.today()}\n",
        "\n",
        f"Includes updates to core through commit: [{CORE_COMMIT[:7]}](https://github.com/PreTeXtBook/pretext/commit/{CORE_COMMIT})\n",
    ]

    new_changelog = []
    with open("CHANGELOG.md", "r") as f:
        # Read entire file into a list of lines
        changelog = f.readlines()
        for line in changelog:
            if line.startswith("## [Unreleased]"):
                new_changelog.append("## [Unreleased]\n")
                new_changelog += insert_lines
            else:
                new_changelog.append(line)
    with open("CHANGELOG.md", "w") as f:
        f.writelines(new_changelog)


if __name__ == "__main__":
    main()
