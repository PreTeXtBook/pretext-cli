<?xml version="1.0" encoding="UTF-8"?>
<!-- A target's own stylesheet, to test that it still applies when the -->
<!-- target builds a single division.                                  -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:import href="./core/pretext-latex.xsl"/>
<xsl:param name="latex.preamble.late" select="'%% CUSTOM-XSL-MARKER'"/>
</xsl:stylesheet>
