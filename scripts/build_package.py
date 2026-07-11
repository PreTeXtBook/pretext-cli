import subprocess
import sys
import fetch_core


def main() -> None:
    import pretext

    arguments = sys.argv[1:]
    print(f"Building package for version {pretext.VERSION}.")
    # ensure up-to-date "static" resources
    fetch_core.main(arguments, update_templates=True)

    # Build package
    subprocess.run(["uv", "build"], shell=True)
    print("Completed uv build of pretext")


if __name__ == "__main__":
    main()
