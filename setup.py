# We use poetry and pyproject.toml, not setup.py.
# To capture projects on GitHub using such versions we fake a setup.py here.

raise Exception("File provided to satisfy GitHub only.")

setup(name="pretext")  # noqa: F821
