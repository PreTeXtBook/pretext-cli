# PreTeXt-CLI

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

Documentation for end-users is available at 
<https://pretextbook.github.io/pretext-cli/>.

Documentation for developers is available below.

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
python build.py
```

## Versioning

See [VERSIONING.md](VERSIONING.md).

## PreTeXt XSL

Right now, we're mirroring resources from
<https://github.com/rbeezer/mathbook/> using the commit
found in `pretext/static/CORE_COMMIT`.
(TODO: pull/build these without mirroring)
<div align='right'></div>