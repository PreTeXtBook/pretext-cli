# PreTeXt-CLI

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

-   GitHub: <https://github.com/PreTeXtBook/pretext-cli/>

## Documentation and examples for authors/publishers

Most documentation for PreTeXt authors and publishers is available at:

-   <https://pretextbook.org/doc/guide/html/>

Authors and publishers may also find the examples catalog useful as well:

-   <https://pretextbook.org/examples.html>

We have a few notes below (TODO: publish these in the Guide).

### Installation

#### Installing Python

PreTeXt-CLI requires the Python version specified in `pyproject.toml`.

To check your version, type this into your terminal or command prompt:

```
python -V
```

If your version is 2.x, try this instead
(and if so, replace all future references to `python`
in these instructions with `python3`).

```
python3 -V
```

If you don't have a compatible Python available, try one of these:

-   https://www.python.org/downloads/
    -   Windows warning: Be sure to select the option adding Python to your Path.
-   https://github.com/pyenv/pyenv#installation (Mac/Linux)
-   https://github.com/pyenv-win/pyenv-win#installation (Windows)

#### Installing PreTeXt-CLI

Once you've confirmed that you're using a valid version of Python, just
run (replacing `python` with `python3` if necessary):

```
python -m pip install --user pretext
```

(It's possible you will get an error like
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

#### External dependencies

We install as much as we can with the `pip install` command, but depending on your machine
you may require some extra software:

-   [TeXLive](https://www.tug.org/texlive/)
-   [pdftoppm/Ghostscript](https://github.com/abarker/pdfCropMargins/blob/master/doc/installing_pdftoppm_and_ghostscript.rst)

#### Upgrading PreTeXt-CLI

If you have an existing installation and you want to upgrade to a more recent version, you can run:

```
python -m pip install --upgrade pretext
```

#### Custom XSL

Custom XSL is not encouraged for most authors, but (for example) developers working
bleeding-edge XSL from core PreTeXt may want to call XSL different from that
which is shipped with a fixed version of the CLI. This may be accomplished by
adding an `<xsl/>` element to your target with a relative (to `project.ptx`) or
absolute path to the desired XSL. _(Note: this XSL must only import
other XSL files in the same directory or within subdirectories.)_

For example:

```
<target name="html">
  <format>html</format>
  <source>source/main.ptx</source>
  <publication>publication/publication.ptx</publication>
  <output-dir>output/html</output-dir>
  <xsl>../pretext/xsl/pretext-html.xsl</xsl>
</target>
```

If your custom XSL file needs to import the XSL
shipped with the CLI (e.g. `pretext-common.xsl`), then use a `./core/`
prefix in your custom XSL's `xsl:import@href` as follows:

```
<xsl:import href="./core/pretext-common.xsl"/>
```

Similarly, `entities.ent` may be used:

```
<!DOCTYPE xsl:stylesheet [
    <!ENTITY % entities SYSTEM "./core/entities.ent">
    %entities;
]>
```

_Note: previously this was achieved with a `pretext-href` attribute - this is now deprecated and will be removed in a future release._

---
## Using this package as a library/API

We have started documenting how you can use this CLI programmatically in [docs/api.md](docs/api.md).

---

## Development

**Note.** The remainder of this documentation is intended only for those interested
in contributing to the development of this project. Anyone who simply wishes to
_use_ the PreTeXt-CLI can stop reading here.

From the "Clone or Download" button on GitHub, copy the `REPO_URL` into the below
command to clone the project.

```bash
git clone [REPO_URL]
cd pretext-cli
```

### Using a valid Python installation

Developers and contributors must install a
version of Python that matching the requirements in `pyproject.toml`.


### Installing dependencies
<details>
<summary><b>Optional</b>: use pyenv as a virtual environment</summary>

The `pyenv` tool for Linux automates the process of running the correct
version of Python when working on this project (even if you have
other versions of Python installed on your system).

-   https://github.com/pyenv/pyenv#installation

Run the following, replacing `PYTHON_VERSION` with your desired version.

```
pyenv install PYTHON_VERSION
```
#### Steps on Windows

In windows, you can either use the bash shell and follow the directions above,
or try [pyenv-win](https://github.com/pyenv-win/pyenv-win#installation). In
the latter case, make sure to follow all the installation instructions, including
the **Finish the installation**. Then proceed to follow the directions above to
install a version of python matching `pyproject.toml`. Finally, you may then need
to manually add that version of python to your path.

</details>

<br/>

The first time you set up your development environment, you should follow these steps:

1. Follow these instructions to install `poetry`.

    -   https://python-poetry.org/docs/#installation
        -   Note 2022/06/21: you may ignore "This installer is deprecated". See
            [python-poetry/poetry/issues/4128](https://github.com/python-poetry/poetry/issues/4128)

2. Install dependencies into a virtual environment with this command.

    ```
    poetry install
    ```

3. Fetch a copy of the core pretext library and bundle templates by running

    ```
    poetry run python scripts/fetch_core.py
    ```

The last command above should also be run when returning to development after some time, since the core commit you develop against might have changed.


Make sure you are in a `poetry shell` during development mode so that you
execute the development version of `pretext-cli` rather than the system-installed
version.

```
pretext --version # returns system version
poetry shell
pretext --version # returns version being developed
```

When inside a `poetry shell` you can navigate to other folders and run pretext commands.  Doing so will use the current development environment version of pretext.


### Updating dependencies
<details>
<summary>Show instructions</summary>
To add dependencies for the package, run

```
poetry add DEPENDENCY-NAME
```

If someone else has added a dependency:

```
poetry install
```
</details>


### Using a local copy of `PreTeXtBook/pretext`

See [docs/core_development.md](docs/core_development.md).



### Formatting code before a commit

All `.py` files are formatted with the [black](https://black.readthedocs.io/en/stable/)
python formatter and checked by [flake8](https://flake8.pycqa.org/en/latest/).
Proper formatting is enforced by checks in the Continuous Integration framework.
Before you commit code, you should make sure it is formatted with `black` and
passes `flake8` by running the following commands (on linux or mac)
from the _root_ project folder (most likely `pretext-cli`).

```
poetry run black .
poetry run flake8
```

### Testing

Sets are contained in `tests/`. To run all tests:

```
poetry run pytest
```

To run a specific test, say `test_name` inside `test_file.py`:

```
poetry run pytest -k name
```

Tests are automatically run by GitHub Actions when pushing to identify
regressions.

### Packaging

To check if a successful build is possible:

```
poetry run python scripts/build_package.py
```

To publish a new alpha release, first add/commit any changes. Then
the following handles bumping versions, publishing to PyPI,
and associated Git management.

```
poetry run python scripts/release_alpha.py
```

Publishing a stable release is similar:

```
poetry run python scripts/release_stable.py # patch +0.+0.+1
poetry run python scripts/release_stable.py minor # +0.+1.0
poetry run python scripts/release_stable.py major # +1.0.0
```

---

## About

### PreTeXt-CLI Team

-   [Oscar Levin](https://math.oscarlevin.com/) is co-creator and lead developer of PreTeXt-CLI.
-   [Steven Clontz](https://clontz.org/) is co-creator and a regular contributor of PreTeXt-CLI.
-   Development of PreTeXt-CLI would not be possible without the frequent
    [contributions](https://github.com/PreTeXtBook/pretext-cli/graphs/contributors) of the
    wider [PreTeXt-Runestone Open Source Ecosystem](https://prose.runestone.academy).

### A note and special thanks

A `pretext` package unrelated to the PreTeXtBook.org project was released on PyPI
several years ago by Alex Willmer. We are grateful for his willingness to transfer
this namespace to us.

As such, versions of this project before 1.0 are released on PyPI under the
name `pretextbook`, while versions 1.0 and later are released as `pretext`.

### About PreTeXt

The development of [PreTeXt's core](https://github.com/PreTeXtBook/pretext)
is led by [Rob Beezer](http://buzzard.ups.edu/).
