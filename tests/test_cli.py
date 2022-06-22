import subprocess, os, glob, shutil
from tempfile import TemporaryDirectory
from pathlib import Path
import pretext

EXAMPLES_DIR = Path(__file__).parent/'ptx'

def pretext_new_cd():
    subprocess.run(["pretext","new"])
    os.chdir(Path("new-pretext-project"))

def test_version():
    cp = subprocess.run(['pretext', '--version'], capture_output=True, text=True)
    assert cp.stdout.strip() == pretext.VERSION

def test_new(tmp_path:Path):
    os.chdir(tmp_path)
    assert subprocess.run(['pretext', 'new', '-d', 'foobar']).returncode == 0
    assert (Path('foobar')/'project.ptx').exists()

def test_build(tmp_path:Path):
    os.chdir(tmp_path)
    pretext_new_cd()
    subprocess.run(['pretext', 'build', 'web'])
    assert (Path('output')/'web').exists()
    subprocess.run(['pretext', 'build', 'print-latex'])
    assert (Path('output')/'print-latex').exists()

def test_init(tmp_path:Path):
    os.chdir(tmp_path)
    fresh = Path('fresh').resolve()
    fresh.mkdir()
    refresh = Path('refresh').resolve()
    refresh.mkdir()
    os.chdir(fresh)
    assert subprocess.run(['pretext', 'init']).returncode == 0
    assert Path('project.ptx').exists()
    assert Path('requirements.txt').exists()
    assert Path('.gitignore').exists()
    assert Path('publication/publication.ptx').exists()
    os.chdir(refresh)
    pretext_new_cd()
    assert subprocess.run(['pretext', 'init']).returncode == 0
    assert len(glob.glob('project-*.ptx')) == 0 # need to refresh
    assert subprocess.run(['pretext', 'init', '-r']).returncode == 0
    assert len(glob.glob('project-*.ptx')) > 0 # need to refresh
    assert len(glob.glob('requirements-*.txt')) > 0
    assert len(glob.glob('.gitignore-*')) > 0
    assert len(glob.glob('publication/publication-*.ptx')) > 0

def test_generate(tmp_path:Path):
    os.chdir(tmp_path)
    subprocess.run(['pretext', 'init'])
    Path('source').mkdir()
    shutil.copyfile(EXAMPLES_DIR/'asymptote.ptx',Path('source')/'main.ptx')
    assert subprocess.run(['pretext','generate','web','-a','asymptote']).returncode == 0
    assert (Path('generated-assets')/'asymptote'/'test.html').exists()
