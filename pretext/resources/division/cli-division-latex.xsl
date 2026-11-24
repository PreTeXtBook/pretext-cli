<?xml version="1.0" encoding="UTF-8"?>
<!-- Build one division of a document as its own LaTeX document. -->
<!-- See "cli-division-common.xsl" for the approach.              -->
<!DOCTYPE xsl:stylesheet [
    <!ENTITY % entities SYSTEM "./core/entities.ent">
    %entities;
]>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal"
    extension-element-prefixes="exsl"
    exclude-result-prefixes="pi">

<!-- The CLI rewrites this "href" to a target's own custom stylesheet, -->
<!-- when it has one, so that both apply.                              -->
<xsl:import href="./core/pretext-latex.xsl"/>
<xsl:include href="cli-division-common.xsl"/>

<!-- ######## -->
<!-- Counters -->
<!-- ######## -->

<!-- LaTeX numbers divisions, blocks and equations with its own      -->
<!-- counters, which would all start from zero here.  So each one is -->
<!-- set from the number stamped on the full document: an ancestor's -->
<!-- counter to its own number, and the counter of anything that is  -->
<!-- about to be stepped to one less than the number it should get.  -->

<!-- An ancestor renders as nothing, but sets its counter -->
<xsl:template match="*[@pi:division = 'ancestor']">
    <xsl:call-template name="division-set-counter">
        <xsl:with-param name="value" select="@pi:serial"/>
    </xsl:call-template>
    <xsl:apply-templates select="*[@pi:division]"/>
</xsl:template>

<xsl:template match="*[@pi:division = 'root']">
    <!-- a division with no number of its own steps no counter -->
    <xsl:variable name="numberless-suffix">
        <xsl:apply-templates select="." mode="division-environment-name-suffix"/>
    </xsl:variable>
    <xsl:if test="$numberless-suffix = ''">
        <xsl:call-template name="division-set-counter">
            <xsl:with-param name="value" select="@pi:serial - 1"/>
        </xsl:call-template>
    </xsl:if>
    <!-- The first numbered item on each counter says where that      -->
    <!-- counter stands.  If a division inside this one resets the    -->
    <!-- counter before that item, the item's number is 1, the value  -->
    <!-- set here is 0, and nothing is disturbed.                     -->
    <xsl:variable name="counters-rtf">
        <xsl:apply-templates select="descendant::*[@pi:serial]" mode="division-counter"/>
    </xsl:variable>
    <xsl:for-each select="exsl:node-set($counters-rtf)/counter[not(@name = preceding-sibling::counter/@name)]">
        <xsl:text>\setcounter{</xsl:text>
        <xsl:value-of select="@name"/>
        <xsl:text>}{</xsl:text>
        <xsl:value-of select="@serial - 1"/>
        <xsl:text>}&#xa;</xsl:text>
    </xsl:for-each>
    <xsl:apply-imports/>
</xsl:template>

<!-- A division's LaTeX counter is named as its level is. Some  -->
<!-- serial numbers are not numbers (a "part" may be a Roman    -->
<!-- numeral), and some divisions have none: those are skipped. -->
<xsl:template name="division-set-counter">
    <xsl:param name="value"/>
    <xsl:if test="string(number($value)) != 'NaN'">
        <xsl:text>\setcounter{</xsl:text>
        <xsl:apply-templates select="." mode="division-name"/>
        <xsl:text>}{</xsl:text>
        <xsl:value-of select="$value"/>
        <xsl:text>}&#xa;</xsl:text>
    </xsl:if>
</xsl:template>

<!-- Which LaTeX counter numbers an item.  The matches and the tests -->
<!-- follow the "serial-stamp" templates of core's assembly, and the -->
<!-- names follow the "auto counter" boxes of core's LaTeX preamble. -->
<!-- TODO: footnotes are not handled.                                -->
<xsl:template match="*" mode="division-counter"/>

<xsl:template match="&DEFINITION-LIKE;|&THEOREM-LIKE;|&AXIOM-LIKE;|&REMARK-LIKE;|&COMPUTATION-LIKE;|&EXAMPLE-LIKE;" mode="division-counter">
    <counter name="tcb@cnt@block" serial="{@pi:serial}"/>
</xsl:template>

<xsl:template match="&PROJECT-LIKE;" mode="division-counter">
    <xsl:call-template name="division-block-counter">
        <xsl:with-param name="distinct" select="$b-number-project-distinct"/>
        <xsl:with-param name="name" select="'projectdistinct'"/>
    </xsl:call-template>
</xsl:template>

<xsl:template match="*[&TOP-FIGURE-FILTER;]" mode="division-counter">
    <xsl:call-template name="division-block-counter">
        <xsl:with-param name="distinct" select="$b-number-figure-distinct"/>
        <xsl:with-param name="name" select="'figuredistinct'"/>
    </xsl:call-template>
</xsl:template>

<xsl:template match="exercise[&INLINE-EXERCISE-FILTER;]" mode="division-counter">
    <xsl:call-template name="division-block-counter">
        <xsl:with-param name="distinct" select="$b-number-exercise-distinct"/>
        <xsl:with-param name="name" select="'exercisedistinct'"/>
    </xsl:call-template>
</xsl:template>

<xsl:template match="&OPENPROBLEM-LIKE;" mode="division-counter">
    <xsl:call-template name="division-block-counter">
        <xsl:with-param name="distinct" select="$b-number-openproblem-distinct"/>
        <xsl:with-param name="name" select="'openproblemdistinct'"/>
    </xsl:call-template>
</xsl:template>

<xsl:template match="mrow[@pi:numbered = 'yes']" mode="division-counter">
    <counter name="equation" serial="{@pi:serial}"/>
</xsl:template>

<!-- a group of blocks runs on its own counter, or shares the blocks' -->
<xsl:template name="division-block-counter">
    <xsl:param name="distinct"/>
    <xsl:param name="name"/>
    <counter serial="{@pi:serial}">
        <xsl:attribute name="name">
            <xsl:text>tcb@cnt@</xsl:text>
            <xsl:choose>
                <xsl:when test="$distinct">
                    <xsl:value-of select="$name"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:text>block</xsl:text>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:attribute>
    </counter>
</xsl:template>

<!-- ################ -->
<!-- Cross-references -->
<!-- ################ -->

<!-- A target still in the full tree is not in this document, so   -->
<!-- LaTeX cannot look up its number, and it is written literally. -->
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

<!-- ##### -->
<!-- Title -->
<!-- ##### -->

<!-- An "article" prints a title block whenever it has a title, and  -->
<!-- here that title is the division's, which the division's heading -->
<!-- is about to print as well.  This template supplies the title    -->
<!-- block's content; in its place, switch the block off.            -->
<xsl:template name="title-page-info-article">
    <xsl:text>%% The title is the heading of the one division built&#xa;</xsl:text>
    <xsl:text>\renewcommand{\maketitle}{}&#xa;</xsl:text>
</xsl:template>

</xsl:stylesheet>
