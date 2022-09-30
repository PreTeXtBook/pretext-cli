import subprocess, pretext
import build_package
from pathlib import Path
from urllib.request import urlopen
import json
from datetime import datetime
import fileinput
# import toml
import tomli

def commit_data(repo):
    lastcommit = {}
    url = f"https://api.github.com/repos/pretextbook/{repo}/commits"
    response = urlopen(url)
    data = json.loads(response.read())
    lastcommit['date'] = datetime.strptime(data[0]['commit']['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
    lastcommit['sha'] = data[0]['sha']
    return lastcommit

def should_release(coredate,clidate):
    if (datetime.now() - coredate).days< 1:
        print(f"There has been an update to core pretext in the last 24 hours, at {coredate}")
        return True
    elif (datetime.now() - clidate).days < 1:
        print(f"There has been an update to the CLI in the last 24 hours, at {clidate}")
        return True
    else:
        return False

def main():
    last_core_commit = commit_data('pretext')
    last_cli_commit = commit_data('pretext-cli')

    # Check to see if there is nothing new to build and stop script if so.
    if not(should_release(last_core_commit['date'], last_cli_commit['date'])):
        print("No recent commits to pretext core of the CLI.  No nightly will be built.")
        return

    # Update core commit (temporarily):
    for line in fileinput.input(Path(__file__).parent.parent/"pretext/__init__.py", inplace=True):
      if 'CORE_COMMIT' in line:
        print(line.replace(line, f"CORE_COMMIT = '{last_core_commit['sha']}'".rstrip()))
      else:
        print(line.rstrip())

    # Update version (temporarily) in pyproject.toml:
    for line in fileinput.input(Path(__file__).parent.parent/"pyproject.toml", inplace=True):
      if 'version' in line:
        version = str(line.split('"')[1])
        newversion = version+".dev"+datetime.now().strftime('%Y%m%d-%H%M%S')
        print(line.replace(line, f'version = "{newversion}"'.rstrip()))
      else:
        print(line.rstrip())
    return    
    # data = toml.load("pyproject.toml")
    # print(data['tool']['poetry']['version'])

    build_package.main()

    print(f"Publishing alpha {pretext.VERSION}")

    # Publish alpha
    subprocess.run(["poetry", "publish"], shell=True)

    # Tag + push
    tag = repo.create_tag(f"v{pretext.VERSION}")
    repo.remotes.origin.push(tag.path)

    # Bump alpha version
    subprocess.run(["poetry", "version", "prerelease"], shell=True)
    # Add/commit/push change
    repo.git.add("pyproject.toml")
    repo.index.commit("Bump version to new alpha")
    repo.remotes.origin.push()

if __name__ == '__main__':
    main()