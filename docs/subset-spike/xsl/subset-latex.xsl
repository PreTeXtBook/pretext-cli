<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal">
<xsl:import href="./core/pretext-latex.xsl"/>
<xsl:include href="subset-common.xsl"/>

<!-- LaTeX numbers headings and blocks with its own counters, so each -->
<!-- invisible ancestor sets its counter to its own number, and the   -->
<!-- division's counter is left one short of its number.              -->
<xsl:template match="*[@pi:subset = 'ancestor']">
    <xsl:if test="@pi:serial != ''">
        <xsl:text>\setcounter{</xsl:text>
        <xsl:apply-templates select="." mode="division-name"/>
        <xsl:text>}{</xsl:text>
        <xsl:value-of select="@pi:serial"/>
        <xsl:text>}&#xa;</xsl:text>
    </xsl:if>
    <xsl:apply-templates select="*[@pi:subset]"/>
</xsl:template>

<xsl:template match="*[@pi:subset = 'root']">
    <xsl:if test="@pi:serial != ''">
        <xsl:text>\setcounter{</xsl:text>
        <xsl:apply-templates select="." mode="division-name"/>
        <xsl:text>}{</xsl:text>
        <xsl:value-of select="@pi:serial - 1"/>
        <xsl:text>}&#xa;</xsl:text>
    </xsl:if>
    <xsl:apply-imports/>
</xsl:template>

<!-- A target still in the full tree is not in this PDF, so LaTeX -->
<!-- cannot look its number up: write the number literally.       -->
<xsl:template match="*" mode="xref-number-latex">
    <xsl:param name="xref" select="/.."/>
    <xsl:choose>
        <xsl:when test="generate-id(/) = generate-id($serial-stamp)">
            <xsl:apply-templates select="." mode="xref-number-hardcoded">
                <xsl:with-param name="xref" select="$xref"/>
            </xsl:apply-templates>
        </xsl:when>
        <xsl:otherwise>
            <xsl:apply-imports/>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>
</xsl:stylesheet>
