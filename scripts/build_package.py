import subprocess
import fetch_core


def main() -> None:
    import pretext

    print(f"Building package for version {pretext.VERSION}.")

    # ensure up-to-date "static" resources
    fetch_core.main()
    # bundle_resources.main() not needed; now part of fetch_core.main()

    # Build package
    subprocess.run(["poetry", "build"], shell=True)
    print("Completed poetry build of pretext")


if __name__ == "__main__":
    main()
