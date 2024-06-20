import shutil
import glob
import tempfile
from pathlib import Path


def main() -> None:
    static_template_path = Path("pretext") / "templates" / "resources"
    print(f"Zipping templates from source into `{static_template_path}`.")

    for template_directory in glob.iglob("templates/[!.]*"):
        template_path = Path(template_directory)
        if template_path.is_dir():
            with tempfile.TemporaryDirectory(prefix="pretext_") as temporary_directory:
                temporary_path = Path(temporary_directory)
                shutil.copytree(
                    template_path,
                    temporary_path,
                    dirs_exist_ok=True,
                )
                template_files = [
                    "project.ptx",
                    ".gitignore",
                    "codechat_config.yaml",
                    ".devcontainer.json",
                ]
                for template_file in template_files:
                    copied_template_file = temporary_path / template_file
                    if not copied_template_file.is_file():
                        shutil.copyfile(
                            Path("templates") / template_file,
                            copied_template_file,
                        )
                template_zip_basename = template_path.name
                shutil.make_archive(
                    str(static_template_path / template_zip_basename),
                    "zip",
                    temporary_path,
                )
    for f in [
        "codechat_config.yaml",
        "project.ptx",
        "publication.ptx",
        ".gitignore",
        ".devcontainer.json",
        "pretext-cli.yml",
    ]:
        shutil.copyfile(Path("templates") / f, static_template_path / f)

    with open(static_template_path / "__init__.py", "w") as _:
        pass

    print(f"Templates successfully zipped into `{static_template_path}`.")


if __name__ == "__main__":
    main()
