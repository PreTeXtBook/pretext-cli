import shutil, glob, tempfile
from pathlib import Path

def main():
    static_template_path = Path('pretext')/'static'/'templates'
    print(f'Zipping templates from source into `{static_template_path}`.')

    for template_directory in glob.iglob('templates/*'):
        template_path = Path(template_directory)
        if template_path.is_dir():
            with tempfile.TemporaryDirectory() as temporary_directory:
                temporary_path = Path(temporary_directory)
                shutil.copytree(
                    template_path,
                    temporary_path,
                    dirs_exist_ok=True,
                )
                template_files = ['project.ptx', '.gitignore']
                for template_file in template_files:
                    copied_template_file = temporary_path/template_file
                    if not copied_template_file.is_file():
                        shutil.copyfile(
                            Path('templates')/template_file,
                            copied_template_file,
                        )
                template_zip_basename = template_path.name
                shutil.make_archive(
                    static_template_path/template_zip_basename,
                    'zip',
                    temporary_path,
                )
    for f in ['project.ptx','publication.ptx','.gitignore']:
        shutil.copyfile(
            Path('templates')/f,
            static_template_path/f
        )

    print(f'Templates successfully zipped into `{static_template_path}`.')

if __name__ == '__main__':
    main()
