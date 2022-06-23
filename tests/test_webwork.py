import subprocess, os, glob, shutil, time, signal, platform, random
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import contextmanager
import requests
import pretext

EXAMPLES_DIR = Path(__file__).parent/'examples'

def pretext_new_cd() -> None:
    subprocess.run(["pretext","new"])
    os.chdir(Path("new-pretext-project"))

def test_custom_webwork_server(tmp_path:Path):
    shutil.copytree(EXAMPLES_DIR/'projects'/'custom-wwserver',tmp_path/'custom')
    os.chdir(tmp_path/'custom')
    assert 'webwork-dev' in str(subprocess.run(["pretext","generate","webwork"], capture_output=True).stdout)
