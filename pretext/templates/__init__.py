from pathlib import Path
import importlib.resources

def resource_path(filename:str) -> Path:
    """
    Returns resource manager
    Usage:
    with resource_path('foo.bar') as filepath:
        # do things
    """
    from . import resources
    return importlib.resources.path(resources,filename)
