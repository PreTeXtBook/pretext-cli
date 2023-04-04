from pathlib import Path
from urllib.request import urlopen
import json
from datetime import datetime
import fileinput


def commit_data(repo):
    lastcommit = {}
    url = f"https://api.github.com/repos/pretextbook/{repo}/commits"
    response = urlopen(url)
    data = json.loads(response.read())
    lastcommit["date"] = datetime.strptime(
        data[0]["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ"
    )
    lastcommit["sha"] = data[0]["sha"]
    return lastcommit


def should_release(coredate, clidate):
    if (datetime.now() - coredate).days < 1:
        print(
            f"There has been an update to core pretext in the last 24 hours, at {coredate}"
        )
        return True
    elif (datetime.now() - clidate).days < 1:
        print(f"There has been an update to the CLI in the last 24 hours, at {clidate}")
        return True
    else:
        return True


def main():
    last_core_commit = commit_data("pretext")
    last_cli_commit = commit_data("pretext-cli")

    # Check to see if there is nothing new to build and stop script if so.
    if not (should_release(last_core_commit["date"], last_cli_commit["date"])):
        print(
            "No recent commits to pretext core or the CLI.  No nightly will be built."
        )
        return

    # Update core commit (temporarily):
    for line in fileinput.input(
        Path(__file__).parent.parent / "pretext/__init__.py", inplace=True
    ):
        if "CORE_COMMIT" in line:
            print(
                line.replace(
                    line, f"CORE_COMMIT = '{last_core_commit['sha']}'".rstrip()
                )
            )
        else:
            print(line.rstrip())

    # Update version (temporarily) in pyproject.toml:
    for line in fileinput.input(
        Path(__file__).parent.parent / "pyproject.toml", inplace=True
    ):
        if line.startswith("version"):
            version = str(line.split('"')[1])
            newversion = version + ".dev" + datetime.now().strftime("%Y%m%d")
            print(line.replace(line, f'version = "{newversion}"'.rstrip()))
        else:
            print(line.rstrip())

    # Need to wait to import build_package until now so it gets the updated version CORE_COMMIT and version.
    import build_package

    build_package.main()


if __name__ == "__main__":
    main()
