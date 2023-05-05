from pathlib import Path
from urllib.request import urlopen
import json
from datetime import datetime
import fileinput


def commit_data(repo):
    """
    Returns a dictionary containing the date and commit sha from the most recent commit to `repo`
    """
    lastcommit = {}
    url = f"https://api.github.com/repos/pretextbook/{repo}/commits"
    response = urlopen(url)
    data = json.loads(response.read())
    lastcommit["date"] = datetime.strptime(
        data[0]["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ"
    )
    lastcommit["sha"] = data[0]["sha"]
    return lastcommit


def main():
    last_core_commit = commit_data("pretext")

    # Update core commit:
    for line in fileinput.input(
        Path(__file__).parent.parent / "pretext/__init__.py", inplace=True
    ):
        if "CORE_COMMIT" in line:
            print(
                line.replace(
                    line, f"CORE_COMMIT = \"{last_core_commit['sha']}\"".rstrip()
                )
            )
        else:
            print(line.rstrip())


if __name__ == "__main__":
    main()
