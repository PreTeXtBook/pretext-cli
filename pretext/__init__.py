from . import static

def version():
    with open(static.path('VERSION'), 'r') as version_file:
        return version_file.read().strip()