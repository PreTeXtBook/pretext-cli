# PreTeXt.py

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

## Lead Contributors

- [Steven Clontz](https://clontz.org)
- Oscar Levin

## Installation

TODO

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

To add dependencies for the package, update `setup.py`. then run `pipenv update`.

To add dependencies for the development environment, use `pipenv install [package]`.

## PreTeXt XSL

Right now, we're developing against this frozen snapshot of PreTeXt:
<https://github.com/rbeezer/mathbook/commit/05339c6b7e29d629c9d8680d6b18985425a100d6>