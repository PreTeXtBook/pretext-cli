<?xml version="1.0" encoding="UTF-8"?>
<!-- Build one division of a document as its own HTML page. -->
<!-- See "cli-division-common.xsl" for the approach.         -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal"
    exclude-result-prefixes="pi">

<!-- The CLI rewrites this "href" to a target's own custom stylesheet, -->
<!-- when it has one, so that both apply.                              -->
<xsl:import href="./core/pretext-html.xsl"/>
<xsl:include href="cli-division-common.xsl"/>

<!-- A division is one page, whatever chunking the publication file -->
<!-- asks of the whole document, and one page needs no table of     -->
<!-- contents (which would also list the ancestors).  Core's EPUB   -->
<!-- conversion overrides the same two variables.                   -->
<xsl:variable name="chunk-level" select="number(0)"/>
<xsl:variable name="toc-level" select="number(0)"/>

<!-- With no table of contents core still writes one, into a hidden -->
<!-- sidebar.  Its entries would be the ancestors, so it gets none. -->
<xsl:template match="*" mode="toc-items"/>

<!-- There is no other page to go to -->
<xsl:template match="*" mode="previous-button"/>
<xsl:template match="*" mode="next-button"/>
<xsl:template match="*" mode="up-button"/>

<!-- One page is searched with the browser, so no search box, no -->
<!-- search script, and no index for it to load                  -->
<xsl:variable name="has-native-search" select="false()"/>

<!-- An ancestor renders as nothing -->
<xsl:template match="*[@pi:division = 'ancestor']">
    <xsl:apply-templates select="*[@pi:division]"/>
</xsl:template>

</xsl:stylesheet>
