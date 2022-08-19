import subprocess, pretext
import fetch_core, zip_templates

def main():
    print(f"Building package for version {pretext.VERSION}.")

    # ensure up-to-date "static" resources
    fetch_core.main()
    zip_templates.main()

    # Build package
    subprocess.run(["poetry", "build"], shell=True)

if __name__ == '__main__':
    main()