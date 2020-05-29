# PreTeXt.py

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

## Lead Contributors

- [Steven Clontz](https://clontz.org)
- Oscar Levin

## Development

From the "Clone or Download" button on GitHub, copy the `repo_url` into the below command to clone the project.

```bash
git clone [repo_url]
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

Then, use `pipenv run [foo]` to run individual scripts, e.g.:

```
$ pipenv run python
Python 3.6.9 (default, Apr 18 2020, 01:56:04) 
[GCC 8.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import pretext
b'<pretext><article><p>Hello PreTeXt World!</p></article></pretext>'
```

Or use `pipenv shell` to enter the virtual environment directly.

To add dependencies for the package, update `setup.py`. then run `pipenv update`.

To add dependencies for the development environment, use `pipenv install [package]`.

## PreTeXt XSL

Right now, we're developing against this frozen snapshot of PreTeXt:
<https://github.com/rbeezer/mathbook/commit/cf93da622c6177bbc3eefc79a11cfdcc0b971c99>