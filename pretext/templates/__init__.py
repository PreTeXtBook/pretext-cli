from pathlib import Path
import importlib.resources as ir


def resource_path(filename: str) -> Path:
    """
    Returns resource manager
    Usage:
    with resource_path('foo.bar') as filepath:
        # do things
    """
    from . import resources

    # Try except here is to use newer importlib function,
    # supported starting with 3.9, and required with 3.11
    try:
        return ir.as_file(ir.files(resources).joinpath(filename))
    except AttributeError:
        return ir.path(resources, filename)
