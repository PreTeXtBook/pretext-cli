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

Install and configure `pyenv` to ensure you're using the minimum Python
specified in `.python-version`.

- https://github.com/pyenv/pyenv#installation

```bash
$ pyenv install "$(cat .python-version)"
(installs version set in `.python-version`)
$ which python
/home/user/.pyenv/shims/python
$ python -V
Python (version set in `.python-version`)
```

Install `pipenv` to manage your Python packages:

```bash
python -m pip install --upgrade pip
python -m pip install pipenv
```

Then all additional dependencies can be installed as a one-liner:

```bash
python -m pipenv install --dev
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

To add dependencies for the package, update `setup.py`. then run `python -m pipenv update`.

To add dependencies for the development environment, use `python -m pipenv install [package]`.

## Packaging

See <https://packaging.python.org/tutorials/packaging-projects/>.
Inside a virtual environment:

```
python build.py
```

## Versioning

See [VERSIONING.md](VERSIONING.md).

## PreTeXt "Core"

Right now, we're mirroring resources from
<https://github.com/rbeezer/mathbook/> using the commit
found in `pretext/static/CORE_COMMIT`.
(TODO: pull/build these without mirroring)
<div align='right'></div>