import subprocess
import fetch_core
import scripts.bundle_resources as bundle_resources


def main() -> None:
    import pretext

    print(f"Building package for version {pretext.VERSION}.")

    # ensure up-to-date "static" resources
    fetch_core.main()
    bundle_resources.main()

    # Build package
    subprocess.run(["poetry", "build"], shell=True)
    print("Completed poetry build of pretext")


if __name__ == "__main__":
    main()
