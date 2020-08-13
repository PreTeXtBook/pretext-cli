import os
from contextlib import contextmanager
import configobj

@contextmanager
def working_directory(path):
    """
    Temporarily change the current working directory.

    Usage:
    with working_directory(path):
        do_things()   # working in the given path
    do_other_things() # back to original path
    """
    current_directory=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current_directory)


def ensure_directory(path):
    """
    If the directory doesn't exist yet, create it.
    """
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def directory_exists(path):
    """
    Checks if the directory exists.
    """
    return os.path.exists(path)

# Write config file
def write_config(configfile, **kwargs):
    config = configobj.ConfigObj(configfile, unrepr=True)
    # config.filename = configfile
    # config["source"] = source
    # config["output"] = output
    # etc:
    for key, value in kwargs.items():
        config[key] = value
    config.write()
    print("Saving options to the config file {}".format(configfile))
    with open(configfile) as cf:
        print(cf.read())


# Taken from Rob's pretext-core:
# These are consistent with pretext-core. 
#   to use elsewhere, write, e.g., utils._verbos('message')
# In any function that imports pretext-core, pass verbosity by 
#   using ptxcore.set_verbosity(utils._verbosity)
def set_verbosity(v):
    """Set how chatty routines are at console: 0, 1, or 2"""
    # 0 - nothing
    # 1 - _verbose() only
    # 2 - _verbose() and _debug()
    global _verbosity

    if ((v != 0) and (v != 1) and (v != 2)):
        print(
            'PTX-CLI:WARNING: verbosity level above 2 has no additional effect')
    _verbosity = v


def _verbose(msg):
    """Write a message to the console on program progress"""
    if _verbosity >= 1:
        print('PTX-CLI: {}'.format(msg))


def _debug(msg):
    """Write a message to the console with some raw information"""
    if _verbosity >= 2:
        print('PTX-CLI:DEBUG: {}'.format(msg))
