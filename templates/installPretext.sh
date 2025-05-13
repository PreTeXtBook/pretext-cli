#!/usr/bin/env bash

# This file was automatically generated with PreTeXt 2.18.1.
# If you modify this file, PreTeXt will no longer automatically update it.

sudo apt-get update 
sudo apt-get install -y --no-install-recommends \
                    python3-louis \
                    libcairo2-dev \
                    librsvg2-bin

pip install --upgrade pip --break-system-packages

pip install pretext[homepage,prefigure] pycairo --only-binary {greenlet}  --break-system-packages

pip install codechat-server --break-system-packages

playwright install-deps

playwright install


# echo '/usr/lib/python3/dist-packages' > /usr/local/lib/python3.8/dist-packages/louis.pth
prefig init

# Install mermaid for diagrams
npm install -g @mermaid-js/mermaid-cli

echo "PreTeXt installation complete."
