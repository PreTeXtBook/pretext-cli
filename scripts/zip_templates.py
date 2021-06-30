import shutil,glob,os

for template_path in glob.iglob('templates/*'):
    if '.ptx' in template_path:
        next
    template_name = os.path.basename(template_path)
    shutil.make_archive(
        os.path.join('pretext','static','templates',template_name),
        'zip',
        template_path,
    )