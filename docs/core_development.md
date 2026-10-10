# Using the CLI when developing on core pretext

The CLI bundles a frozen version of the core python script, as well as the corresponding support files (xsl, css, js, etc).  But because of this, it is not possible for the CLI to use a local version of the core python script.  This means that if you are developing on the core python script and want to test with the CLI, you will need to install the CLI from source.

This guide will walk you through the process of installing the CLI from source and linking the core resources to your local version of the pretext repository.

## Installing the CLI from source

We will assume you have a local clone of the pretext repository in a directory parallel to a local clone of the pretext-cli repository.  

If you don't have these yet, you can clone them with the following commands:

```bash
git clone https://github.com/PreTeXtBook/pretext-cli.git
git clone https://github.com/PreTeXtBook/pretext.git
```

To install the CLI from source, we follow the same instructions as in the development section of the README.

<details>
<summary>Show instructions</summary>
First, navigate to the pretext-cli directory and install the CLI with the following commands:

```bash
cd pretext-cli
uv sync --all-extras
python ./scripts/fetch_core.py
```

You should now be able to test that everything worked by running the following commands:

```bash
pretext --version # You should get the version installed with PIP
uv run pretext --version # You should get the newer version installed with uv
```

At this point, it is probably easiest to activate the virtual environment `uv sync` created at `.venv` so you don't have to prefix every command with `uv run`.

```bash
source .venv/bin/activate # on Windows: .venv\Scripts\activate
```

Now when you run `pretext --version` you should get the version installed with uv.
</details>

## Linking the core resources

The CLI has a script `script\symlink_core.py` that will create symbolic links from the CLI's `core` directory to the core directory in the pretext repository.  This script will also create a `core` directory in the CLI's `pretext` directory and link the core resources there as well.  This is necessary because the CLI uses the core resources from the `pretext` directory, not the `core` directory. 

Assuming you have the pretext and pretext-cli repositories in the same directory, you can run the following command to link the core resources:

```bash
python ./scripts/symlink_core.py
```

If you have the pretext repository elsewhere, you can specify the path to the pretext repository as an argument to the script:

```bash
python ./scripts/symlink_core.py /path/to/pretext
```

Now any changes you make the python script, xsl, css, js, or schema in the pretext repository will be reflected in the CLI (just stay in the activated virtual environment).

To check whether the CLI is currently linked, run

```bash
uv run python -c "from pathlib import Path; print(Path('pretext/core/pretext.py').is_symlink())"
```

which prints `True` when the CLI is using your local pretext repository.

### On Windows

Windows only lets ordinary users create symbolic links when Developer Mode is turned on (Settings → System → For developers → Developer Mode). Without it, `symlink_core.py` fails with `OSError: [WinError 1314] A required privilege is not held by the client`. Either turn on Developer Mode (recommended, and needed only once) or run the script from a terminal opened with "Run as administrator".

The commands in this guide work in PowerShell, Command Prompt, or Git Bash, except for activating the virtual environment, which is `.venv\Scripts\activate` on Windows. If `python` opens the Microsoft Store or is not found, use `uv run python` (or `py`) instead.

#### Using Claude Code (or another coding agent) on Windows

The pretext repository has `AGENTS.md` files (read by Claude Code through its `CLAUDE.md`) that tell an agent how to validate and build, with commands like `python3 pretext/pretext -V full ... -d /tmp/sa-check ...`. On Windows, Claude Code runs these commands in Git Bash, which understands the `/tmp` paths and the `(cd ... && npm ...)` syntax. The one command that usually fails is `python3`: it is often missing or opens the Microsoft Store, and an agent that hits this tends to waste time looking for a working Python. Tell the agent which Python to use in a `CLAUDE.local.md` file at the root of your pretext checkout. The pretext repository gitignores that file and Claude Code reads it alongside the shared instructions. The virtual environment created for the CLI is a good choice, since it already has the packages core needs (all except `nbformat`, which is used only for Jupyter notebook output). For example:

```markdown
This is a Windows machine; shell commands run in Git Bash.
Wherever the instructions say `python3`, use `../pretext-cli/.venv/Scripts/python.exe` instead.
```

You can also note where `jing`, `xsltproc`, and `trang` are installed, or say that they are not, so the agent skips those checks rather than trying to install them. To apply the same notes in every repository on that computer, put them in `~/.claude/CLAUDE.md` (your user folder's `.claude\CLAUDE.md`) instead.

## Unlinking the core resources

To go back to using the version of core resources specified in the `CORE_COMMIT` file, you can run the following command:

```bash
python ./scripts/unlink_core.py
```
