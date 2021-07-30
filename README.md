# PreTeXt-CLI

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

- GitHub: <https://github.com/PreTeXtBook/pretext-cli/>

## Documentation and examples for authors/publishers

This README is written for the PreTeXt developer community.
Documentation for PreTeXt authors and publishers is available at:

- https://pretextbook.org/documentation.html

Authors and publishers may also find the examples catalog useful as well:

- https://pretextbook.org/examples.html

---

## Installation

### Installing Python

PreTeXt-CLI requires the Python version specified in `.python-version`.

To check your version, type this into your terminal or command prompt:

```
python -V
```

If your version is 2.x, try this instead
(and if so, either replace all future references to `python`
in these instructions with `python3`).

```
python3 -V
```

If you don't have a compatible Python available, try one of these:

- https://www.python.org/downloads/
  - Windows warning: Be sure to select the option adding Python to your Path.
- https://github.com/pyenv/pyenv#installation (Mac/Linux)
- https://github.com/pyenv-win/pyenv-win#installation (Windows)

### Installing PreTeXt-CLI

Once you've confirmed that you're using a valid version of Python, just
run (replacing `python` with `python3` if necessary):

```
python -m pip install --user pretextbook
```

(It's also possible you may get an error like 
`error: invalid command 'bdist_wheel'`
— good news, you can ignore it!)

After installation, try to run:

```
pretext --help
```

If that works, great! Otherwise, it likely means that Python packages
aren't available on your “PATH”. In that case, replace all `pretext`
commands with `python -m pretext` instead:

```
python -m pretext --help
```

Either way, you're now ready to use the CLI, the `--help` option will explain how to use all the different
subcommands like `pretext new` and `pretext build`.

## Development

From the "Clone or Download" button on GitHub, copy the `REPO_URL` into the below command to clone the project.

```bash
git clone [REPO_URL]
cd pretext-cli
```

### Using a valid Python installation

Developers and contributors are highly encouraged to install the exact
version of Python that is specified in `.python-version`. All instructions
assume that the Python on your path (e.g. the result of `python -V`)
matches this version.

#### Using pyenv (Mac/Linux)

The `pyenv` tool for Linux automates the process of running the correct
version of Python when working on this project (even if you have
other versions of Python installed on your system).

- https://github.com/pyenv/pyenv#installation

```bash
$ pyenv install "$(cat .python-version)"
    # installs version set in `.python-version`
$ which python
/home/user/.pyenv/shims/python
$ python -V
Python (version set in `.python-version`)
```

#### Steps on Windows

In windows, you can either use the bash shell and follow the directions above, or try [pyenv-win](https://github.com/pyenv-win/pyenv-win#installation).  In the latter case, make sure to follow all the installation instructions, including the **Finish the installation**.  Then proceed to follow the directions above to install the version of python in `.python-version`.  Finally, you may then need to manually add that version of python to your path.

### Managing packages and virtual environments

Install `pipenv` to manage your Python packages:

```bash
python -m pip install --upgrade pip
python -m pip install pipenv
```

Then all additional dependencies can be installed into
a virtual environment as follows:

```bash
$ python -m pipenv --rm
    # destroy any outdated environment
$ git pull
    # ensures your build versions locked by Pipfile.lock
$ python -m pipenv install --dev
    # creates virtual environment and installs dependencies
```

Then use `python -m pipenv shell` to enter the virtual environment directly.

```
$ python -m pipenv shell
Launching subshell in virtual environment…
$ cd
$ pretext new
Generating new PreTeXt project in `/home/user/new-pretext-project` using `book` template.
```

You can also use `python -m pipenv run [CMD]` for quick runs outside the virtual
environment, e.g.:

```
$ python -m pipenv run pretext new
```

### Updating dependencies

To add dependencies for the package, edit `setup.py`. then run

```
python -m pipenv update
```

To add dependencies for the development environment
(those not needed to use the packaged CLI), use

```
python -m pipenv install [package] --dev
```

To update dependencies added by other contributors, use

```
python -m pipenv sync
```

### Syncing untracked updates

Updates to certain files tracked to the repository will
need to be rebuilt by each user when pulled from GitHub.

The file `pretext/static/CORE_COMMIT` tracks the upstream
commit of core PreTeXt XSL/Python code we're developing against
(from `rbeezer/mathbook`).
To grab these updates from upstream, run:

```
python scripts/update_core.py
```

If you instead want to point to a local copy of `rbeezer/mathbook`,
try this instead to set up symlinks:

```
python scripts/simlink_core.py path/to/mathbook
```

Updates to `templates/` must be zipped and moved into
`pretext/static/templates`. This is done automatically by
running:

```
python scripts/zip_templates.py
```

## Packaging

See <https://packaging.python.org/tutorials/packaging-projects/>.
Inside a virtual environment:

```
python scripts/build_release.py
```

## Versioning

See [VERSIONING.md](VERSIONING.md).

## About

### PreTeXt-CLI Lead Developers
- [Steven Clontz](https://clontz.org/)
- [Oscar Levin](https://math.oscarlevin.com/)

### About PreTeXt
The development of [PreTeXt's core](https://github.com/rbeezer/mathbook)
is led by [Rob Beezer](http://buzzard.ups.edu/).
