#!/usr/bin/env bash

# This file was automatically generated with PreTeXt 2.15.2.
# If you modify this file, PreTeXt will no longer automatically update it.

apt update && apt install -y --no-install-recommends \
    texlive \
    texlive-plain-generic \
    texlive-science \
    texlive-xetex \
    texlive-fonts-extra \
    ghostscript \
    asymptote

apt-get clean && rm -rf /var/lib/apt/lists/*

echo "All done."