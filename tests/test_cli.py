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

@contextmanager
def pretext_view(*args):
    process = subprocess.Popen(['pretext','view']+list(args))
    time.sleep(1)
    try:
        yield process
    finally:
        process.send_signal(signal.SIGINT)
        time.sleep(1)
        assert process.poll()==0

def cmd_works(*args) -> bool:
    return subprocess.run(args).returncode == 0

def test_entry_points():
    assert cmd_works('pretext', '-h')
    assert cmd_works('python', '-m', 'pretext', '-h')

def test_version():
    cp = subprocess.run(['pretext', '--version'], capture_output=True, text=True)
    assert cp.stdout.strip() == pretext.VERSION

def test_new(tmp_path:Path):
    os.chdir(tmp_path)
    assert cmd_works('pretext', 'new', '-d', 'foobar')
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
    assert cmd_works('pretext', 'init')
    assert Path('project.ptx').exists()
    assert Path('requirements.txt').exists()
    assert Path('.gitignore').exists()
    assert Path('publication/publication.ptx').exists()
    os.chdir(refresh)
    pretext_new_cd()
    assert cmd_works('pretext', 'init')
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
    assert cmd_works('pretext','generate','web','-a','asymptote')
    assert (Path('generated-assets')/'asymptote'/'test.html').exists()

def test_view(tmp_path:Path):
    os.chdir(tmp_path)
    port = random.randint(10_000, 65_636)
    with pretext_view('-d','.','-p',f'{port}'):
        assert requests.get(f'http://localhost:{port}/').status_code == 200
    port+=1
    pretext_new_cd()
    subprocess.run(['pretext','build'])
    with pretext_view('-p',f'{port}'):
        assert requests.get(f'http://localhost:{port}/').status_code == 200
