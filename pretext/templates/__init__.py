from contextlib import AbstractContextManager
import importlib.resources as ir


def resource_path(filename: str) -> AbstractContextManager:
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
        # TODO: remove the ignore when Python 3.8 support ends. This fails Python 3.8 type checks, since these functions depend on newer Python versions.
        return ir.as_file(ir.files(resources).joinpath(filename))  # type: ignore[attr-defined]
    except AttributeError:
        return ir.path(resources, filename)
