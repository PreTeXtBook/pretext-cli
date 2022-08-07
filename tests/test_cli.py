import subprocess, os, shutil, time, signal, platform, random, sys
from tempfile import TemporaryDirectory
from pathlib import Path
from contextlib import contextmanager
import requests, pytest
import pretext

EXAMPLES_DIR = Path(__file__).parent/'examples'

PTX_CMD = shutil.which("pretext")
PY_CMD = sys.executable

@contextmanager
def pretext_view(*args):
    process = subprocess.Popen([PTX_CMD,'-v','debug','view', '--no-launch']+list(args))
    time.sleep(3) # stall for possible build
    try:
        yield process
    finally:
        process.terminate()
        process.wait()

def test_entry_points(script_runner):
    ret = script_runner.run(PTX_CMD,'-v','debug', '-h')
    assert ret.success
    assert subprocess.run([PY_CMD, '-m', 'pretext','-v','debug', '-h'], shell=True).returncode == 0

def test_version(script_runner):
    ret = script_runner.run(PTX_CMD,'-v','debug', '--version')
    assert ret.stdout.strip() == pretext.VERSION

def test_new(tmp_path:Path,script_runner):
    assert script_runner.run(PTX_CMD,'-v','debug', 'new', cwd=tmp_path).success
    assert (tmp_path/'new-pretext-project'/'project.ptx').exists()

def test_build(tmp_path:Path,script_runner):
    assert script_runner.run(PTX_CMD,'-v','debug', 'new', '-d', '.', cwd=tmp_path).success
    assert script_runner.run(PTX_CMD,'-v','debug', 'build', 'web', cwd=tmp_path).success
    assert (tmp_path/'output'/'web').exists()
    assert script_runner.run(PTX_CMD,'-v','debug', 'build', 'subset', cwd=tmp_path).success
    assert (tmp_path/'output'/'subset').exists()
    assert script_runner.run(PTX_CMD, 'build', 'print-latex', cwd=tmp_path).success
    assert (tmp_path/'output'/'print-latex').exists()
    assert script_runner.run(PTX_CMD,'-v','debug', 'build', '-g', cwd=tmp_path).success
    assert (tmp_path/'generated-assets').exists()
    os.removedirs(tmp_path/'generated-assets')
    assert script_runner.run(PTX_CMD,'-v','debug', 'build', '-g', 'webwork', cwd=tmp_path).success
    assert (tmp_path/'generated-assets').exists()

def test_init(tmp_path:Path,script_runner):
    assert script_runner.run(PTX_CMD,'-v','debug', 'init', cwd=tmp_path).success
    assert (tmp_path/'project.ptx').exists()
    assert (tmp_path/'requirements.txt').exists()
    assert (tmp_path/'.gitignore').exists()
    assert (tmp_path/'publication'/'publication.ptx').exists()
    assert len([*tmp_path.glob('project-*.ptx')]) == 0 # need to refresh
    assert script_runner.run(PTX_CMD,'-v','debug', 'init', '-r', cwd=tmp_path).success
    assert len([*tmp_path.glob('project-*.ptx')]) > 0
    assert len([*tmp_path.glob('requirements-*.txt')]) > 0
    assert len([*tmp_path.glob('.gitignore-*')]) > 0
    assert len([*tmp_path.glob('publication/publication-*.ptx')]) > 0

def test_generate_asymptote(tmp_path:Path,script_runner):
    assert script_runner.run(PTX_CMD,'-v','debug', 'init', cwd=tmp_path).success
    (tmp_path/'source').mkdir()
    shutil.copyfile(EXAMPLES_DIR/'asymptote.ptx',tmp_path/'source'/'main.ptx')
    assert script_runner.run(PTX_CMD,'-v','debug','generate','asymptote', cwd=tmp_path).success
    assert (tmp_path/'generated-assets'/'asymptote'/'test.html').exists()
    os.remove(tmp_path/'generated-assets'/'asymptote'/'test.html')
    assert script_runner.run(PTX_CMD,'-v','debug','generate','-x', 'test', cwd=tmp_path).success
    assert (tmp_path/'generated-assets'/'asymptote'/'test.html').exists()
    os.remove(tmp_path/'generated-assets'/'asymptote'/'test.html')
    assert script_runner.run(PTX_CMD,'-v','debug','generate','asymptote','-t', 'web', cwd=tmp_path).success
    os.remove(tmp_path/'generated-assets'/'asymptote'/'test.html')

@pytest.mark.skip(reason="Waiting on upstream changes to interactive preview generation")
def test_generate_interactive(tmp_path:Path,script_runner):
    int_path = tmp_path/'interactive'
    shutil.copytree(EXAMPLES_DIR/'projects'/'interactive',int_path)
    assert script_runner.run(PTX_CMD,'-v','debug','generate', cwd=int_path).success
    preview_file = int_path/'generated-assets'/'preview'/'calcplot3d-probability-wavefunction.png'
    assert preview_file.exists()


def test_view(tmp_path:Path,script_runner):
    os.chdir(tmp_path)
    port = random.randint(10_000, 65_536)
    with pretext_view('-d','.','-p',f'{port}'):
        assert requests.get(f'http://localhost:{port}/').status_code == 200
    assert script_runner.run(PTX_CMD,'-v','debug',"new","-d",'1').success
    os.chdir(Path('1'))
    assert script_runner.run(PTX_CMD,'-v','debug','build').success
    port = random.randint(10_000, 65_536)
    with pretext_view('-p',f'{port}'):
        assert requests.get(f'http://localhost:{port}/').status_code == 200
    os.chdir(tmp_path)
    assert script_runner.run(PTX_CMD,'-v','debug',"new","-d",'2').success
    os.chdir(Path('2'))
    port = random.randint(10_000, 65_536)
    with pretext_view('-p',f'{port}','-b','-g'):
        assert requests.get(f'http://localhost:{port}/').status_code == 200

def test_custom_xsl(tmp_path:Path,script_runner):
    custom_path = tmp_path/'custom'
    shutil.copytree(EXAMPLES_DIR/'projects'/'custom-xsl',custom_path)
    assert script_runner.run(PTX_CMD,'-v','debug','build', cwd=custom_path).success
    assert (custom_path/'output'/'test').exists()
    assert script_runner.run(PTX_CMD,'-v','debug','build', 'test-deprecated', cwd=custom_path).success
    assert (custom_path/'output'/'test-deprecated').exists()

def test_custom_webwork_server(tmp_path:Path,script_runner):
    custom_path = tmp_path/'custom'
    shutil.copytree(EXAMPLES_DIR/'projects'/'custom-wwserver',custom_path)
    result = script_runner.run(PTX_CMD,'-v','debug','generate','webwork', cwd=custom_path)
    assert result.success
    assert 'webwork-dev' in result.stderr
    result = script_runner.run(PTX_CMD,'-v','debug','build', cwd=custom_path)
    assert result.success

def test_slideshow(tmp_path:Path,script_runner):
    assert script_runner.run(PTX_CMD,'-v','debug', 'new', 'slideshow', '-d', '.', cwd=tmp_path).success
    assert script_runner.run(PTX_CMD,'-v','debug', 'build', 'web', cwd=tmp_path).success
    assert (tmp_path/'output'/'web'/'slides.html').exists()
