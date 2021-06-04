# PreTeXt-CLI

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

Documentation for end-users is available at 
<https://pretextbook.github.io/pretext-cli/>.

Documentation for developers is available below.

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
$ pretext new "My Great Book"
Generating new PreTeXt project in `my-great-book`.
```

You can also use `python -m pipenv run [CMD]` for quick runs outside the virtual
environment, e.g.:

```
$ python -m pipenv run pretext new "My Great Book"
Generating new PreTeXt project in `my-great-book`.
```

### Updating dependencies

To add dependencies for the package, edit `setup.py`. then run

```
python -m pipenv update
```

To add dependencies for the development environment, use

```
python -m pipenv install [package]
```

## Packaging

See <https://packaging.python.org/tutorials/packaging-projects/>.
Inside a virtual environment:

```
python scripts/build_release.py
```

## Versioning

See [VERSIONING.md](VERSIONING.md).

## PreTeXt "Core"

Right now, we're mirroring resources from
<https://github.com/rbeezer/mathbook/> using the commit
found in `pretext/static/CORE_COMMIT`.
These can be updated by running:

```
python scripts/update_core.py
```
