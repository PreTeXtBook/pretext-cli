<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal">
<xsl:import href="./core/pretext-html.xsl"/>
<xsl:include href="subset-common.xsl"/>
<!-- an intermediate ancestor is invisible -->
<xsl:template match="*[@pi:subset = 'ancestor']">
    <xsl:apply-templates select="*[@pi:subset]"/>
</xsl:template>
</xsl:stylesheet>
