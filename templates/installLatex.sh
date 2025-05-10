#!/usr/bin/env bash

# This file was automatically generated with PreTeXt 2.18.1.
# If you modify this file, PreTeXt will no longer automatically update it.

# We use TinyTeX (https://yihui.org/tinytex/)
wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh

tlmgr install adjustbox amscdx bold-extra braket bussproofs cancel carlisle cases chessfss circuitikz colortbl enumitem extpfeil fontawesome5 fontaxes gensymb imakeidx jknapltx kastrup lambda-lists listings listingsutf8 marvosym mathalpha mathtools menukeys mhchem microtype musicography newpx newtx nicematrix pdfcol pdfpages pdflscape pgfplots phaistos physics polyglossia pstricks realscripts relsize siunitx skak skaknew smartdiagram snapshot stmaryrd tcolorbox tikz-cd tikzfill titlesec txfonts ulem upquote was xfrac xltxtra xpatch xstring 

tlmgr path add

#  Ensure fonts provided by TinyTeX are available, as suggested in the pretext guide
fontconfig="<?xml version=\"1.0\"?>
<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">
<fontconfig>
  <dir>~/.TinyTeX/texmf-dist/fonts</dir>
  <dir>~/.TinyTeX/texmf-local/fonts</dir>
</fontconfig>"

fontconfig_path="/etc/fonts/conf.d/09-texlive-fonts.conf"
if [ ! -f "$fontconfig_path" ]; then
    echo "Creating fontconfig file at $fontconfig_path"
    echo "$fontconfig" | sudo tee "$fontconfig_path" > /dev/null
else
    echo "Fontconfig file already exists at $fontconfig_path"
fi
# Update font cache
fc-cache -f -v
