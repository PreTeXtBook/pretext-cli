from pathlib import Path
import importlib.resources
from . import resources

def resource_path(filename:str) -> Path:
    """
    Returns resource manager
    Usage:
    with resource_path('foo.bar') as filepath:
        # do things
    """
    return importlib.resources.path(resources,filename)
