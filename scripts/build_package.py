import subprocess, pretext
import update_core, zip_templates

def main():
    print(f"Building package for version {pretext.VERSION}.")

    # ensure up-to-date "static" resources
    update_core.main()
    zip_templates.main()

    # Build package
    subprocess.run(["poetry", "build"])

if __name__ == '__main__':
    main()