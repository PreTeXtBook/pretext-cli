import subprocess, git, sys
import build_package

def main(level='patch'):
    repo = git.Repo()
    if repo.bare or repo.is_dirty() or len(repo.untracked_files)>0:
        raise Exception("Must commit outstanding changes to project source.")

    # Bump stable version
    subprocess.run(["poetry", "version", level])
    # Add/commit change
    repo.git.add("pyproject.toml")
    repo.index.commit("Bump version to new alpha")

    build_package.main()

    import pretext
    print(f"Publishing stable {pretext.VERSION}")

    # Publish stable
    subprocess.run(["poetry", "publish"])

    # Tag
    tag = repo.create_tag(f"v{pretext.VERSION}")

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
