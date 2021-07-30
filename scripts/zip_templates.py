import shutil,glob,os,tempfile

for template_directory in glob.iglob('templates/*'):
    if os.path.isdir(template_directory):
        with tempfile.TemporaryDirectory() as temporary_directory:
            copied_directory = shutil.copytree(
                template_directory,
                temporary_directory,
                dirs_exist_ok=True,
            )
            shutil.copyfile(
                'templates/project.ptx',
                os.path.join(copied_directory,'project.ptx'),
            )
            template_zip_basename = os.path.basename(template_directory)
            shutil.make_archive(
                os.path.join('pretext','static','templates',template_zip_basename),
                'zip',
                copied_directory,
            )
shutil.copyfile('templates/project.ptx','pretext/static/templates/project.ptx' )
shutil.copyfile('templates/publication.ptx','pretext/static/templates/publication.ptx' )
