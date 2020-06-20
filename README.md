# PreTeXt.py

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

## Lead Contributors

- [Steven Clontz](https://clontz.org)
- [Oscar Levin](https://math.oscarlevin.com/)

The development of [PreTeXt's core](https://github.com/rbeezer/mathbook)
is led by [Rob Beezer](http://buzzard.ups.edu/).

## Requirements

Python 3.4 or higher is required. To check your version, type this
into your terminal or command prompt:

```
python -V
```

If your version is 2.x, try this instead
(and if so, either replace all future references to `python`
in these instructions with `python3`, or try
[this](https://askubuntu.com/a/321000) in Linux):

```
python3 -V
```

If you don't have Python 3.4+ available, try one of these:

- https://www.python.org/downloads/
- https://github.com/pyenv/pyenv#installation (Mac/Linux) or https://github.com/pyenv-win/pyenv-win#installation (Windows)

### Additional Dependencies

Certain features of PreTeXt require other software
to be installed. TODO: document this.

## Installation

Once you've confirmed that you're using Python 3.4+,
just run (replacing `python` with `python3` if necessary):

```
python -m pip install pretextbook
```

## Usage

Run `pretext --help` and `pretext [CMD] --help`
on the command line for usage details.

## Development

From the "Clone or Download" button on GitHub, copy the `REPO_URL` into the below command to clone the project.

```bash
git clone [REPO_URL]
cd pretext.py
```

Install `pipenv` to manage your environment:

```bash
python -m pip install --user pipenv # or python3 if necessary
```

Then all dependencies can be installed as a one-liner:

```bash
pipenv install --three
```

Then, use `pipenv run [CMD]` to run individual scripts, e.g.:

```
$ pipenv run pretext new "My Great Book"
Generating new PreTeXt project in `my-great-book`.
```

Or use `pipenv shell` to enter the virtual environment directly.

```
$ pipenv shell
Launching subshell in virtual environment…
$ pretext new "My Great Book"
Generating new PreTeXt project in `my-great-book`.
```

To add dependencies for the package, update `setup.py`. then run `pipenv update`.

To add dependencies for the development environment, use `pipenv install [package]`.

## Packaging

See <https://packaging.python.org/tutorials/packaging-projects/>.

```
python setup.py sdist bdist_wheel
python -m twine upload --repository testpypi dist/* # to test
python -m twine upload dist/* # for real
```

## PreTeXt XSL

Right now, we're developing against this frozen snapshot of PreTeXt:
<https://github.com/rbeezer/mathbook/commit/a770b95e5ac1c5ec39406ec111fa493e1fa90d86>
