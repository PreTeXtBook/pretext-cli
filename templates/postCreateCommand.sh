#!/usr/bin/env bash

# wget https://raw.githubusercontent.com/oscarlevin/pandoc-pretext/master/pretext.lua

echo "Install LaTeX"
apt-get update && apt-get install -y texlive texlive-latex-extra texlive-fonts-extra texlive-xetex texlive-science --no-install-recommends

echo "Install PDF tools"
apt install -y ghostscript pdf2svg --no-install-recommends

echo "Install sage"
apt-get install -y sagemath --no-install-recommends

echo "If your project does not require all these tools, edit '.devcontainer/postCreateCommand.sh' and build a new container.  This is only a concern if you are running out of space in GitHub codespaces."