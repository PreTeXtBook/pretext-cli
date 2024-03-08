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

As in the development directions in the README, we will use poetry to install the CLI from source.  First, navigate to the pretext-cli directory and install the CLI with the following command:

```bash
cd pretext-cli
poetry install
```

You should now be able to test that everything worked by running the following commands:

```bash
pretext --version # You should get the version installed with PIP
poetry run pretext --version # You should get the newer version installed with poetry
```

At this point, it is probably easiest to start a `poetry shell` so you don't have to prefix every command with `poetry run`.

```bash
poetry shell
```

Now when you run `pretext --version` you should get the version installed with poetry.

## Linking the core resources

The CLI has a script `script\symlink_core.py` that will create symbolic links from the CLI's `core` directory to the core directory in the pretext repository.  This script will also create a `core` directory in the CLI's `pretext` directory and link the core resources there as well.  This is necessary because the CLI uses the core resources from the `pretext` directory, not the `core` directory. 

Assuming you have the pretext and pretext-cli repositories in the same directory, you can run the following command to link the core resources:

```bash
python script/symlink_core.py
```

If you have the pretext repository elsewhere, you can specify the path to the pretext repository as an argument to the script:

```bash
python script/symlink_core.py /path/to/pretext
```

Now any changes you make the python script, xsl, css, js, or schema in the pretext repository will be reflected in the CLI (just stay in the `poetry shell`).

## Unlinking the core resources

To go back to using the version of core resources specified in the `CORE_COMMIT` file, you can run the following command:

```bash
python ./script/fetch_core.py
```
