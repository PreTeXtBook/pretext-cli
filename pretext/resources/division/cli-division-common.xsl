<?xml version="1.0" encoding="UTF-8"?>
<!-- Build one division of a document as if it were the whole document. -->
<!--                                                                    -->
<!-- Core's assembly ends with a tree, $serial-stamp, in which every    -->
<!-- numbered element carries its number as attributes (@pi:struct,     -->
<!-- @pi:serial, @pi:level).  The conversions read their input from     -->
<!-- $root, $docinfo and $document-root, which core documents as        -->
<!-- overridable by a conversion.  Here they are overridden with a      -->
<!-- pruned copy of that tree holding only:                             -->
<!--                                                                    -->
<!--   * "docinfo", whole                                               -->
<!--   * the document root, retitled with the division's title          -->
<!--   * each ancestor of the division, as a shell: its attributes, its -->
<!--     title, and the one child leading to the division               -->
<!--   * the division, whole                                            -->
<!--                                                                    -->
<!-- The numbers were stamped on the full document, so the division     -->
<!-- keeps them.  The ancestors stay because core decides much by       -->
<!-- "parent::" and "ancestor::" tests; a format's stylesheet must make -->
<!-- them render as nothing.                                            -->
<!--                                                                    -->
<!-- This file is included, not imported, by a format's stylesheet, so  -->
<!-- its definitions take that stylesheet's precedence over core's.     -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal"
    extension-element-prefixes="exsl"
    exclude-result-prefixes="pi">

<!-- the @xml:id of the division to build, supplied by the CLI -->
<xsl:param name="cli.division" select="''"/>

<xsl:variable name="division-node" select="$serial-stamp//*[@xml:id = $cli.division]"/>
<!-- the division and its ancestors, for membership tests -->
<xsl:variable name="division-lineage" select="$division-node/ancestor-or-self::*"/>

<xsl:variable name="division-rtf">
    <xsl:if test="not($division-node)">
        <xsl:message terminate="yes">PTX:FATAL:   the division to build ("<xsl:value-of select="$cli.division"/>") is not in the assembled source.  It may belong to a version that this publication file leaves out.  Quitting...</xsl:message>
    </xsl:if>
    <xsl:apply-templates select="$serial-stamp/pretext" mode="division-prune"/>
</xsl:variable>

<!-- the "pretext" element: "docinfo" whole, then on toward the division -->
<xsl:template match="pretext" mode="division-prune">
    <xsl:copy>
        <xsl:copy-of select="@*"/>
        <xsl:copy-of select="docinfo"/>
        <xsl:apply-templates select="*[not(self::docinfo)]" mode="division-prune"/>
    </xsl:copy>
</xsl:template>

<!-- the document root: its title becomes the division's title -->
<xsl:template match="pretext/*[not(self::docinfo)]" mode="division-prune">
    <xsl:copy>
        <xsl:copy-of select="@*"/>
        <title>
            <xsl:copy-of select="$division-node/title/node()"/>
        </title>
        <xsl:apply-templates select="*[count(.|$division-lineage) = count($division-lineage)]" mode="division-prune"/>
    </xsl:copy>
</xsl:template>

<!-- The division is copied whole.  An ancestor becomes a shell.  A  -->
<!-- match pattern may not use a variable, so one template does both. -->
<xsl:template match="*" mode="division-prune">
    <xsl:choose>
        <xsl:when test="generate-id(.) = generate-id($division-node)">
            <xsl:copy>
                <xsl:attribute name="pi:division">root</xsl:attribute>
                <xsl:apply-templates select="@*|node()" mode="division-copy"/>
            </xsl:copy>
        </xsl:when>
        <xsl:otherwise>
            <xsl:copy>
                <xsl:attribute name="pi:division">ancestor</xsl:attribute>
                <xsl:copy-of select="@*"/>
                <xsl:copy-of select="title"/>
                <xsl:apply-templates select="*[count(.|$division-lineage) = count($division-lineage)]" mode="division-prune"/>
            </xsl:copy>
        </xsl:otherwise>
    </xsl:choose>
</xsl:template>

<!-- Copy the division, marking each cross-reference whose target is  -->
<!-- outside it.  The visible text cannot be made here: the templates -->
<!-- that make it consult $docinfo, which waits on this very tree.    -->
<xsl:template match="node()|@*" mode="division-copy">
    <xsl:copy>
        <xsl:apply-templates select="node()|@*" mode="division-copy"/>
    </xsl:copy>
</xsl:template>

<!-- TODO: a cross-reference with a list or a range of targets -->
<xsl:template match="xref[@ref and not(contains(normalize-space(@ref), ' ')) and not(contains(@ref, ','))]" mode="division-copy">
    <xsl:variable name="target" select="id(@ref)"/>
    <xsl:copy>
        <xsl:if test="$target and not($target/ancestor-or-self::*[generate-id(.) = generate-id($division-node)])">
            <xsl:attribute name="pi:division-outward">yes</xsl:attribute>
        </xsl:if>
        <xsl:apply-templates select="node()|@*" mode="division-copy"/>
    </xsl:copy>
</xsl:template>

<!-- the overrides of core's input -->
<xsl:variable name="root" select="exsl:node-set($division-rtf)/pretext"/>
<xsl:variable name="docinfo" select="$root/docinfo"/>
<xsl:variable name="document-root" select="$root/*[not(self::docinfo)]"/>

<!-- A cross-reference leaving the division gets its usual visible  -->
<!-- text, made from the target in the full tree, and no link since -->
<!-- there is nothing in this output to link to.                    -->
<xsl:template match="xref[@pi:division-outward = 'yes']">
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
