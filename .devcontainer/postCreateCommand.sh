#!/usr/bin/env bash

echo "Install Poetry and Python dependencies"
curl -sSL https://install.python-poetry.org | python -
echo 'export PATH="/root/.local/bin:$PATH"' > ~/.bashrc
. ~/.bashrc
poetry config virtualenvs.create false
poetry install --with dev
python scripts/fetch_core.py
python scripts/zip_templates.py
playwright install-deps
playwright install
