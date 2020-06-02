def ensure_directory(path):
    """
    If the directory doesn't exist yet, create it.
    """
    import os
    # create directory at path if it doesn't exist:
    try:
        os.makedirs(path)
    except FileExistsError:
        pass


def directory_exists(path):
    """
    Checks if the directory exists.
    """
    import os
    return os.path.exists(path)