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
