import importlib.resources as pkg_resources


def filepath(filename):
    """
    Returns path to files in the static folder of the distribution.
    """
    with pkg_resources.path(__name__, filename) as p:
        static_file = str(p.resolve())
    return static_file
