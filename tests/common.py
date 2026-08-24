"""
Shared helpers for the test suite: the location of the example fixture
projects and a check for the presence of external executables (xelatex, asy,
sage, ...).
"""

from pathlib import Path
import subprocess
from typing import List

# The example projects used as build fixtures throughout the suite.
EXAMPLES_DIR = Path(__file__).parent.resolve() / "examples"


# Return True if the given binary is installed and exits with a return code of 0; otherwise, return False. This provides an easy way to check that a given binary is installed.
def check_installed(
    # The command to run to check that a given binary is installed; for example, `["python", "--version"]` would check that Python is installed.
    subprocess_args: List[str],
) -> bool:
    try:
        subprocess.run(subprocess_args, check=True)
    except Exception:
        return False
    return True
