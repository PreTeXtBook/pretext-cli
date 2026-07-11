#!/usr/bin/env bash

echo "Install uv and Python dependencies"
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'export PATH="/root/.local/bin:$PATH"' > ~/.bashrc
. ~/.bashrc
uv sync --all-extras
uv run python scripts/fetch_core.py
uv run playwright install-deps
uv run playwright install
# Run mypy once so that it will install any needed type stubs. After this, the VSCode extension will run it automatically.
uv run mypy --install-types --non-interactive