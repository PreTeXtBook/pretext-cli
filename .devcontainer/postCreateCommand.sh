#!/usr/bin/env bash

echo "Install Poetry and Python dependencies"
curl -sSL https://install.python-poetry.org | python -
poetry install
poetry run python scripts/fetch_core.py
poetry run python scripts/zip_templates.py

echo "Install LaTeX"
apt update && apt install -y texlive texlive-latex-extra texlive-fonts-extra texlive-xetex texlive-science --no-install-recommends

echo "Install sage"
apt install -y sagemath --no-install-recommends

echo "Install PDF tools"
apt install -y ghostscript pdf2svg --no-install-recommends
