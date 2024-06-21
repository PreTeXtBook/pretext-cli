from pathlib import Path
import subprocess
from typing import List

EXAMPLES_DIR = Path(__file__).parent.resolve() / "examples"

DEMO_MAPPING = {
    "source/main.ptx": ["my-demo-book"],
    "source/frontmatter.ptx": [
        "frontmatter",
        "frontmatter-preface",
    ],
    "source/ch-first with spaces.ptx": ["ch-first-without-spaces"],
    "source/sec-first-intro.ptx": ["sec-first-intro"],
    "source/sec-first-examples.ptx": ["sec-first-examples"],
    "source/ex-first.ptx": ["ex-first"],
    "source/ch-empty.ptx": ["ch-empty"],
    "source/ch-features.ptx": ["ch-features"],
    "source/sec-features.ptx": ["sec-features-blocks"],
    "source/ch-generate.ptx": [
        "ch-generate",
        "sec-latex-image",
        "sec-sageplot",
        "sec-asymptote",
        "sec-webwork",
        "sec-youtube",
        "sec-interactive",
        "interactive-infinity",
        "sec-codelens",
    ],
    "source/backmatter.ptx": ["backmatter"],
}


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
