#!/usr/bin/env bash

# This file was automatically generated with PreTeXt {VERSION}.
# If you modify this file, PreTeXt will no longer automatically update it.

# Detect architecture and download appropriate Pandoc version
if uname -m | grep -q "aarch64\|arm64"; then
    # ARM architecture
    wget https://github.com/jgm/pandoc/releases/download/3.8.3/pandoc-3.8.3-1-arm64.deb -O pandoc.deb
else
    # x86/amd64 architecture
    wget https://github.com/jgm/pandoc/releases/download/3.8.3/pandoc-3.8.3-1-amd64.deb -O pandoc.deb
fi

# wait for 60 second and then double check that no other script is using apt-get:
sleep 60
while fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
    echo "Waiting for apt-get to be free..."
    sleep 15
done
# Install pandoc
apt-get install -y --no-install-recommends ./pandoc.deb 

rm pandoc.deb
