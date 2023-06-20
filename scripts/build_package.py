import subprocess
import fetch_core
import zip_templates


def main() -> None:
    import pretext

    print(f"Building package for version {pretext.VERSION}.")

    # ensure up-to-date "static" resources
    fetch_core.main()
    zip_templates.main()

    # Build package
    subprocess.run(["poetry", "build"], shell=True)
    print("Completed poetry build of pretext")


if __name__ == "__main__":
    main()
