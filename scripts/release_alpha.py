import subprocess, pretext, git
import build_package

def main():
    repo = git.Repo()
    if repo.bare or repo.is_dirty() or len(repo.untracked_files)>0:
        raise Exception("Must commit outstanding changes to project source.")

    build_package.main()

    print(f"Publishing alpha {pretext.VERSION}")

    # Publish alpha
    subprocess.run(["poetry", "publish"])

    # Tag + push
    tag = repo.create_tag(f"v{pretext.VERSION}")
    repo.remotes.origin.push(tag.path)

    # Bump alpha version
    subprocess.run(["poetry", "version", "prerelease"])
    # Add/commit/push change
    repo.git.add("pyproject.toml")
    repo.index.commit("Bump version to new alpha")
    repo.remotes.origin.push()

if __name__ == '__main__':
    main()