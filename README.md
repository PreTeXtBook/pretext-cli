# PreTeXt-CLI

A package for authoring and building [PreTeXt](https://pretextbook.org) documents.

- GitHub: <https://github.com/PreTeXtBook/pretext-cli/>

## Documentation and examples for authors/publishers

Most documentation for PreTeXt authors and publishers is available at:

- <https://pretextbook.org/doc/guide/html/>

Authors and publishers may also find the examples catalog useful as well:

- <https://pretextbook.org/examples.html>

We have a few notes below (TODO: publish these in the Guide).

### Installation

#### Installing Python

PreTeXt-CLI requires the Python version specified in `pyproject.toml`.

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

#### Installing PreTeXt-CLI

Once you've confirmed that you're using a valid version of Python, just
run (replacing `python` with `python3` if necessary):

```
python -m pip install --user pretext
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

#### External dependencies

We install as much as we can with the `pip install` command, but depending on your machine
you may require some extra software:

- [TeXLive](https://www.tug.org/texlive/)
- [pdftoppm/Ghostscript](https://github.com/abarker/pdfCropMargins/blob/master/doc/installing_pdftoppm_and_ghostscript.rst)

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
absolute path to the desired XSL. *(Note: this XSL must only import
other XSL files in the same directory or within subdirectories.)*

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

*Note: previously this was achieved with a `pretext-href` attribute - this is now deprecated and will be removed in a future release.*

---

## Development
**Note.** The remainder of this documentation is intended only for those interested
in contributing to the developement of this project.  Anyone who simply wishes to
*use* the PreTeXt-CLI can stop reading here. 

From the "Clone or Download" button on GitHub, copy the `REPO_URL` into the below
command to clone the project.

```bash
git clone [REPO_URL]
cd pretext-cli
```

### Using a valid Python installation

Developers and contributors must install a
version of Python that matching the requirements in `pyproject.toml`.

#### Using pyenv and poetry (Mac/Linux)

The `pyenv` tool for Linux automates the process of running the correct
version of Python when working on this project (even if you have
other versions of Python installed on your system).

- https://github.com/pyenv/pyenv#installation

Run the following, replacing `PYTHON_VERSION` with your desired version.

```
pyenv install PYTHON_VERSION
```

Then follow these instructions to install `poetry`.

- https://python-poetry.org/docs/#installation
    - Note 2022/06/21: you may ignore "This installer is deprecated". See
      [python-poetry/poetry/issues/4128](https://github.com/python-poetry/poetry/issues/4128)

Then you should be able to install dependencies into a virtual environment
with this command.

```
poetry install
```

Then to use the in-development package, you can either enter a poetry shell:

```
pretext --version # returns system version
poetry shell
pretext --version # returns version being developed
exit
pretext --version # returns system version
```

Or use the runner (as long as you remain within the package directory):

```
pretext --version             # returns system version
poetry run pretext --version  # returns version being developed
```

If you run `echo 'alias pr="poetry run"' >> ~/.bashrc` then restart your
shell, this becomes less of a mouthful:

```
pretext --version     # returns system version
pr pretext --version  # returns version being developed
```

#### Steps on Windows

In windows, you can either use the bash shell and follow the directions above,
or try [pyenv-win](https://github.com/pyenv-win/pyenv-win#installation).  In
the latter case, make sure to follow all the installation instructions, including
the **Finish the installation**.  Then proceed to follow the directions above to
install a version of python matching `.pyproject.toml`.  Finally, you may then need
to manually add that version of python to your path.

### Updating dependencies

To add dependencies for the package, run

```
poetry add DEPENDENCY-NAME
```

If someone else has added a dependency:

```
poetry install
```

### Syncing untracked updates

Updates to certain files tracked to the repository will
need to be rebuilt by each user when pulled from GitHub.

The file `pretext/__init__.py` tracks the upstream
commit of core PreTeXt XSL/Python code we're developing against
(from `PreTeXtBook/pretext`).
To fetch these updates from upstream, run:

```
poetry run python scripts/fetch_core.py
```

If you instead want to point to a local copy of `PreTeXtBook/pretext`,
try this instead to set up symlinks:

```
poetry run python scripts/symlink_core.py path/to/pretext
```

Updates to `templates/` must be zipped and moved into
`pretext/templates/resources`. This is done automatically by
running:

```
poetry run python scripts/zip_templates.py
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

### PreTeXt-CLI Lead Developers
- [Steven Clontz](https://clontz.org/)
- [Oscar Levin](https://math.oscarlevin.com/)

### A note and special thanks

A `pretext` package unrelated to the PreTeXtBook.org project was released on PyPI
several years ago by Alex Willmer. We are grateful for his willingness to transfer
this namespace to us.

As such, versions of this project before 1.0 are released on PyPI under the
name `pretextbook`, while versions 1.0 and later are released as `pretext`.

### About PreTeXt
The development of [PreTeXt's core](https://github.com/PreTeXtBook/pretext)
is led by [Rob Beezer](http://buzzard.ups.edu/).
