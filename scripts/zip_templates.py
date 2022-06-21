import shutil,glob,os,tempfile

def main():
    print('Zipping templates from source into `pretext/static/templates`.')

    for template_directory in glob.iglob('templates/*'):
        if os.path.isdir(template_directory):
            with tempfile.TemporaryDirectory() as temporary_directory:
                copied_directory = shutil.copytree(
                    template_directory,
                    temporary_directory,
                    dirs_exist_ok=True,
                )
                template_files = ['project.ptx', '.gitignore']
                for template_file in template_files:
                    copied_template_file = os.path.join(copied_directory, template_file)
                    if not os.path.isfile(copied_template_file):
                        shutil.copyfile(
                            'templates/'+template_file,
                            copied_template_file,
                        )
                # copied_project_ptx = os.path.join(copied_directory,'project.ptx')
                # if not os.path.isfile(copied_project_ptx):
                #     shutil.copyfile(
                #         'templates/project.ptx',
                #         copied_project_ptx,
                #     )
                template_zip_basename = os.path.basename(template_directory)
                shutil.make_archive(
                    os.path.join('pretext','static','templates',template_zip_basename),
                    'zip',
                    copied_directory,
                )
    shutil.copyfile('templates/project.ptx','pretext/static/templates/project.ptx' )
    shutil.copyfile('templates/publication.ptx','pretext/static/templates/publication.ptx' )
    shutil.copyfile('templates/.gitignore','pretext/static/templates/.gitignore' )

    print('Templates successfully zipped into `pretext/static/templates`.')

if __name__ == '__main__':
    main()
