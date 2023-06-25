#!/usr/bin/env bash

echo "Install Poetry and Python dependencies"
curl -sSL https://install.python-poetry.org | python -
poetry install
poetry config virtualenvs.in-project true
poetry run python scripts/fetch_core.py
poetry run python scripts/zip_templates.py
poetry run playwright install-deps
poetry run playwright install

echo "Update apt"
sudo apt update

echo "Install LaTeX"
sudo apt install -y texlive texlive-latex-extra texlive-fonts-extra texlive-xetex texlive-science --no-install-recommends

echo "Install sage"
sudo apt install -y sagemath --no-install-recommends

echo "Install PDF tools"
sudo apt install -y ghostscript pdf2svg --no-install-recommends
