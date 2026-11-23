<?xml version="1.0" encoding="UTF-8"?>
<!-- SPIKE: prune the fully assembled, numbered tree to one division,   -->
<!-- keeping its chain of ancestors so core's parent/ancestor tests     -->
<!-- still hold.  Included (not imported) so these definitions take the -->
<!-- precedence of the including stylesheet and override core's $root.  -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal"
    extension-element-prefixes="exsl">

<xsl:param name="subset.id" select="''"/>
<xsl:variable name="subset-node" select="$serial-stamp//*[@xml:id = $subset.id]"/>

<xsl:variable name="subset-rtf">
    <xsl:if test="not($subset-node)">
        <xsl:message terminate="yes">SPIKE: no element with xml:id "<xsl:value-of select="$subset.id"/>"</xsl:message>
    </xsl:if>
    <xsl:apply-templates select="$serial-stamp/pretext" mode="subset-prune"/>
</xsl:variable>

<!-- the "pretext" element: keep "docinfo" whole, descend the rest -->
<xsl:template match="pretext" mode="subset-prune">
    <xsl:copy>
        <xsl:copy-of select="@*"/>
        <xsl:copy-of select="docinfo"/>
        <xsl:apply-templates select="*[not(self::docinfo)]" mode="subset-prune"/>
    </xsl:copy>
</xsl:template>

<!-- the document root: its title becomes the division's title -->
<xsl:template match="pretext/*[not(self::docinfo)]" mode="subset-prune">
    <xsl:copy>
        <xsl:copy-of select="@*"/>
        <title><xsl:copy-of select="$subset-node/title/node()"/></title>
        <xsl:apply-templates select="*[count(.|$subset-node/ancestor-or-self::*) = count($subset-node/ancestor-or-self::*)]" mode="subset-prune"/>
    </xsl:copy>
</xsl:template>

<!-- the division itself is copied whole; an intermediate ancestor -->
<!-- keeps its attributes and title, and only the child that leads  -->
<!-- to the division.  (A match pattern may not use a variable, so  -->
<!-- the two cases share a template.)                               -->
<xsl:template match="*" mode="subset-prune">
    <xsl:choose>
        <xsl:when test="generate-id(.) = generate-id($subset-node)">
            <xsl:copy>
                <xsl:attribute name="pi:subset">root</xsl:attribute>
                <xsl:apply-templates select="@*|node()" mode="subset-copy"/>
            </xsl:copy>
        </xsl:when>
        <xsl:otherwise>
            <xsl:copy>
                <xsl:attribute name="pi:subset">ancestor</xsl:attribute>
                <xsl:copy-of select="@*"/>
                <xsl:copy-of select="title"/>
                <xsl:apply-templates select="*[count(.|$subset-node/ancestor-or-self::*) = count($subset-node/ancestor-or-self::*)]" mode="subset-prune"/>
            </xsl:copy>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

<!-- Copy the division, marking each cross-reference whose target lies -->
<!-- outside it.  (The text cannot be made here: the templates that     -->
<!-- make it consult $docinfo, which depends on the tree being built.)  -->
<xsl:template match="node()|@*" mode="subset-copy">
    <xsl:copy>
        <xsl:apply-templates select="node()|@*" mode="subset-copy"/>
    </xsl:copy>
</xsl:template>

<xsl:template match="xref[@ref and not(contains(normalize-space(@ref), ' ')) and not(contains(@ref, ','))]" mode="subset-copy">
    <xsl:variable name="target" select="id(@ref)"/>
    <xsl:copy>
        <xsl:if test="$target and not($target/ancestor-or-self::*[generate-id(.) = generate-id($subset-node)])">
            <xsl:attribute name="pi:subset-outward">yes</xsl:attribute>
        </xsl:if>
        <xsl:apply-templates select="node()|@*" mode="subset-copy"/>
    </xsl:copy>
</xsl:template>

<xsl:variable name="root" select="exsl:node-set($subset-rtf)/pretext"/>
<xsl:variable name="docinfo" select="$root/docinfo"/>
<xsl:variable name="document-root" select="$root/*[not(self::docinfo)]"/>

<!-- A cross-reference leaving the division: its usual visible text, -->
<!-- from the target in the full tree, with no link.                 -->
<xsl:template match="xref[@pi:subset-outward = 'yes']">
    <xsl:variable name="ref" select="@ref"/>
    <xsl:variable name="target" select="$serial-stamp//*[@xml:id = $ref]"/>
    <xsl:variable name="text-style">
        <xsl:apply-templates select="." mode="get-text-style"/>
    </xsl:variable>
    <xsl:apply-templates select="." mode="xref-text">
        <xsl:with-param name="target" select="$target"/>
        <xsl:with-param name="text-style" select="$text-style"/>
        <xsl:with-param name="custom-text">
            <xsl:apply-templates/>
        </xsl:with-param>
    </xsl:apply-templates>
</xsl:template>

</xsl:stylesheet>
