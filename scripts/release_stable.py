import subprocess, git, sys
from pathlib import Path
import tomli
import build_package

def main(level='patch'):
    repo = git.Repo()
    if repo.bare or repo.is_dirty() or len(repo.untracked_files)>0:
        raise Exception("Must commit outstanding changes to project source.")

    # Bump stable version
    subprocess.run(["poetry", "version", level])
    # Add/commit change
    repo.git.add("pyproject.toml")
    repo.index.commit(f"Bump version to new {level}")

    build_package.main()

    with open(Path(__file__).parent.parent/'pyproject.toml', "rb") as f:
        toml_dict = tomli.load(f)
        stable_version = toml_dict['tool']['poetry']['version']
    print(f"Publishing stable {stable_version}")

    # Publish stable
    subprocess.run(["poetry", "publish", "--build"])

    # Tag
    tag = repo.create_tag(f"v{stable_version}")

    # Bump alpha version
    subprocess.run(["poetry", "version", "prerelease"])
    # Add/commit/push change
    repo.git.add("pyproject.toml")
    repo.index.commit("Bump version to new alpha")
    repo.remotes.origin.push()
    repo.remotes.origin.push(tag.path)

if __name__ == '__main__':
    try:
        level = sys.argv[1].lower()
    except IndexError:
        level = "patch"
    assert level in ['major', 'minor', 'patch']
    main(level)
