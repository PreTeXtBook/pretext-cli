import shutil,glob,os

for template_path in glob.iglob('templates/*'):
    if os.path.isdir(template_path):
        template_name = os.path.basename(template_path)
        shutil.make_archive(
            os.path.join('pretext','static','templates',template_name),
            'zip',
            template_path,
        )
shutil.copyfile('templates/project.ptx','pretext/static/templates/project.ptx' )
