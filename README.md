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

Developers and contributors need a version of Python matching the requirements
in `pyproject.toml`. You don't need to install this yourself: [uv](https://docs.astral.sh/uv/),
this project's package/environment manager, can install and manage Python
versions for you (see below).

### Installing dependencies

The first time you set up your development environment, you should follow these steps:

1. Install `uv`.

    -   https://docs.astral.sh/uv/getting-started/installation/

2. Install dependencies into a virtual environment with this command. `uv` will
    automatically download and use a Python version matching `pyproject.toml`
    if one isn't already available on your system&mdash;no separate `pyenv`
    install required.

    ```
    uv sync --all-extras
    ```

3. Fetch a copy of the core pretext library and bundle templates by running

    ```
    uv run python scripts/fetch_core.py
    ```

The last command above should also be run when returning to development after some time, since the core commit you develop against might have changed.


Prefix commands with `uv run` during development mode so that you
execute the development version of `pretext-cli` rather than the system-installed
version.

```
pretext --version # returns system version
uv run pretext --version # returns version being developed
```

Alternatively, you can activate the virtual environment that `uv sync` creates
at `.venv` directly, so you don't have to prefix every command with `uv run`:

```
pretext --version # returns system version
source .venv/bin/activate # on Windows: .venv\Scripts\activate
pretext --version # returns version being developed
```

If you want to develop against a specific Python version (for example, to
reproduce a bug reported against an older version), you can ask `uv` to use
it directly:

```
uv python install 3.11   # downloads the interpreter if you don't have it
uv sync --all-extras --python 3.11
```

### Updating dependencies
<details>
<summary>Show instructions</summary>
To add dependencies for the package, run

```
uv add DEPENDENCY-NAME
```

If someone else has added a dependency:

```
uv sync --all-extras
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
uv run black .
uv run flake8
```

### Testing

Sets are contained in `tests/`. To run all tests:

```
uv run pytest
```

To run a specific test, say `test_name` inside `test_file.py`:

```
uv run pytest -k name
```

Tests are automatically run by GitHub Actions when pushing to identify
regressions.

### Packaging

To check if a successful build is possible:

```
uv run python scripts/build_package.py
```

Releases (both nightly and stable) are handled by the `deploy-nightly` and
`deploy-stable` GitHub Actions workflows, which bump the version, build the
package with `uv build`, and publish with `uv publish`. Trigger `deploy-stable`
manually from the Actions tab to cut a release.

### Asset generation

Generating assets is complicated.  See [docs/asset-generation.md](docs/asset-generation.md)

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
