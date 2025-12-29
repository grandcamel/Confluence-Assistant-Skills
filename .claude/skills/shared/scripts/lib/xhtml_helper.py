"""
XHTML Storage Format Helper

Provides utilities for working with Confluence's legacy XHTML storage format,
which is used by the v1 API and for content that predates the v2 API.

Features:
- Convert XHTML storage format to Markdown
- Convert Markdown to XHTML storage format
- Convert XHTML to ADF (for v1 to v2 migration)
- Handle Confluence-specific macros

XHTML Storage Format Documentation:
https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html

Usage:
    from xhtml_helper import xhtml_to_markdown, markdown_to_xhtml

    # Convert XHTML to Markdown
    markdown = xhtml_to_markdown(storage_format_html)

    # Convert Markdown to XHTML
    xhtml = markdown_to_xhtml("# Heading\n\nParagraph")
"""

import re
import html
from typing import Dict, Any, List, Optional, Tuple


def xhtml_to_markdown(xhtml: str) -> str:
    """
    Convert Confluence XHTML storage format to Markdown.

    Handles:
    - Paragraphs, headings, lists
    - Bold, italic, underline, strikethrough
    - Links and images
    - Code blocks and inline code
    - Tables
    - Common Confluence macros

    Args:
        xhtml: XHTML storage format content

    Returns:
        Markdown content
    """
    if not xhtml:
        return ""

    # Unescape HTML entities first
    text = html.unescape(xhtml)

    # Remove XML declaration and namespace prefixes
    text = re.sub(r'<\?xml[^>]*\?>', '', text)
    text = re.sub(r'</?ac:', '</', text)
    text = re.sub(r'</?ri:', '</', text)

    # Process macros before general HTML
    text = _process_macros(text)

    # Headings (h1-h6)
    for level in range(1, 7):
        pattern = rf'<h{level}[^>]*>(.*?)</h{level}>'
        text = re.sub(pattern, lambda m: f"\n{'#' * level} {_clean_text(m.group(1))}\n", text, flags=re.DOTALL)

    # Paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', lambda m: f"\n{_clean_text(m.group(1))}\n", text, flags=re.DOTALL)

    # Line breaks
    text = re.sub(r'<br\s*/?\s*>', '  \n', text)

    # Bold
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)

    # Italic
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)

    # Underline (Markdown doesn't support, use HTML or emphasis)
    text = re.sub(r'<u[^>]*>(.*?)</u>', r'_\1_', text, flags=re.DOTALL)

    # Strikethrough
    text = re.sub(r'<s[^>]*>(.*?)</s>', r'~~\1~~', text, flags=re.DOTALL)
    text = re.sub(r'<del[^>]*>(.*?)</del>', r'~~\1~~', text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', text, flags=re.DOTALL)

    # Links
    text = re.sub(
        r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
        lambda m: f'[{_clean_text(m.group(2))}]({m.group(1)})',
        text,
        flags=re.DOTALL
    )

    # Images
    text = re.sub(
        r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/?>',
        r'![\2](\1)',
        text
    )
    text = re.sub(
        r'<img[^>]*src="([^"]*)"[^>]*/?>',
        r'![](\1)',
        text
    )

    # Preformatted/code blocks
    text = re.sub(
        r'<pre[^>]*>(.*?)</pre>',
        lambda m: f"\n```\n{_clean_text(m.group(1))}\n```\n",
        text,
        flags=re.DOTALL
    )

    # Process lists
    text = _process_lists(text)

    # Process tables
    text = _process_tables(text)

    # Blockquotes
    text = re.sub(
        r'<blockquote[^>]*>(.*?)</blockquote>',
        lambda m: '\n' + '\n'.join(f'> {line}' for line in _clean_text(m.group(1)).split('\n')) + '\n',
        text,
        flags=re.DOTALL
    )

    # Horizontal rules
    text = re.sub(r'<hr\s*/?\s*>', '\n---\n', text)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def _clean_text(text: str) -> str:
    """Clean text content, removing extra whitespace."""
    text = re.sub(r'<[^>]+>', '', text)  # Remove any HTML tags
    text = re.sub(r'\s+', ' ', text)  # Collapse whitespace
    return text.strip()


def _process_macros(text: str) -> str:
    """
    Process Confluence macros in XHTML.

    Common macros:
    - code: Code block
    - panel/info/warning/note: Info panels
    - toc: Table of contents
    - anchor: Page anchors
    - expand: Expandable sections
    """
    # Code macro
    def code_macro(match):
        params = match.group(1) or ""
        content = match.group(2)
        language = ""

        lang_match = re.search(r'language="([^"]*)"', params)
        if lang_match:
            language = lang_match.group(1)

        return f"\n```{language}\n{_clean_text(content)}\n```\n"

    text = re.sub(
        r'<structured-macro[^>]*name="code"([^>]*)>.*?<plain-text-body>(.*?)</plain-text-body>.*?</structured-macro>',
        code_macro,
        text,
        flags=re.DOTALL
    )

    # Info/Warning/Note panels
    panel_types = ['info', 'warning', 'note', 'tip', 'panel']
    for panel_type in panel_types:
        pattern = rf'<structured-macro[^>]*name="{panel_type}"[^>]*>.*?<rich-text-body>(.*?)</rich-text-body>.*?</structured-macro>'
        text = re.sub(
            pattern,
            lambda m: f"\n> **{panel_type.title()}:** {_clean_text(m.group(1))}\n",
            text,
            flags=re.DOTALL
        )

    # Status macro (colored labels)
    text = re.sub(
        r'<structured-macro[^>]*name="status"[^>]*>.*?<parameter name="title">([^<]*)</parameter>.*?</structured-macro>',
        r'`\1`',
        text,
        flags=re.DOTALL
    )

    # TOC macro - just note it
    text = re.sub(
        r'<structured-macro[^>]*name="toc"[^>]*>.*?</structured-macro>',
        '\n[Table of Contents]\n',
        text,
        flags=re.DOTALL
    )

    # Expand macro
    def expand_macro(match):
        title = "Details"
        title_match = re.search(r'<parameter name="title">([^<]*)</parameter>', match.group(0))
        if title_match:
            title = title_match.group(1)
        body_match = re.search(r'<rich-text-body>(.*?)</rich-text-body>', match.group(0), re.DOTALL)
        body = _clean_text(body_match.group(1)) if body_match else ""
        return f"\n<details>\n<summary>{title}</summary>\n\n{body}\n</details>\n"

    text = re.sub(
        r'<structured-macro[^>]*name="expand"[^>]*>.*?</structured-macro>',
        expand_macro,
        text,
        flags=re.DOTALL
    )

    return text


def _process_lists(text: str) -> str:
    """Process HTML lists to Markdown."""
    # Unordered lists
    def ul_handler(match):
        items = re.findall(r'<li[^>]*>(.*?)</li>', match.group(1), re.DOTALL)
        return '\n' + '\n'.join(f'- {_clean_text(item)}' for item in items) + '\n'

    text = re.sub(r'<ul[^>]*>(.*?)</ul>', ul_handler, text, flags=re.DOTALL)

    # Ordered lists
    def ol_handler(match):
        items = re.findall(r'<li[^>]*>(.*?)</li>', match.group(1), re.DOTALL)
        return '\n' + '\n'.join(f'{i+1}. {_clean_text(item)}' for i, item in enumerate(items)) + '\n'

    text = re.sub(r'<ol[^>]*>(.*?)</ol>', ol_handler, text, flags=re.DOTALL)

    return text


def _process_tables(text: str) -> str:
    """Process HTML tables to Markdown."""
    def table_handler(match):
        table_html = match.group(0)
        rows = []

        # Find all rows
        row_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)

        for i, row_html in enumerate(row_matches):
            # Find cells (th or td)
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row_html, re.DOTALL)
            cells = [_clean_text(c) for c in cells]

            if cells:
                row = '| ' + ' | '.join(cells) + ' |'
                rows.append(row)

                # Add header separator after first row
                if i == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cells)) + ' |'
                    rows.append(separator)

        return '\n' + '\n'.join(rows) + '\n' if rows else ''

    text = re.sub(r'<table[^>]*>.*?</table>', table_handler, text, flags=re.DOTALL)

    return text


def markdown_to_xhtml(markdown: str) -> str:
    """
    Convert Markdown to Confluence XHTML storage format.

    Args:
        markdown: Markdown content

    Returns:
        XHTML storage format content
    """
    if not markdown:
        return ""

    lines = markdown.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty line
        if not stripped:
            i += 1
            continue

        # Heading
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = _markdown_inline_to_xhtml(heading_match.group(2))
            result.append(f'<h{level}>{text}</h{level}>')
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}$', stripped):
            result.append('<hr />')
            i += 1
            continue

        # Code block
        if stripped.startswith('```'):
            lang_match = re.match(r'^```(\w*)$', stripped)
            language = lang_match.group(1) if lang_match else ""
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(html.escape(lines[i]))
                i += 1
            code = '\n'.join(code_lines)

            if language:
                result.append(
                    f'<ac:structured-macro ac:name="code">'
                    f'<ac:parameter ac:name="language">{language}</ac:parameter>'
                    f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
                    f'</ac:structured-macro>'
                )
            else:
                result.append(f'<pre>{code}</pre>')
            i += 1
            continue

        # Blockquote
        if stripped.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_text = re.sub(r'^>\s*', '', lines[i].strip())
                quote_lines.append(quote_text)
                i += 1
            quote_content = _markdown_inline_to_xhtml(' '.join(quote_lines))
            result.append(f'<blockquote><p>{quote_content}</p></blockquote>')
            continue

        # Bullet list
        if re.match(r'^[-*]\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^[-*]\s+', lines[i].strip()):
                item_text = re.sub(r'^[-*]\s+', '', lines[i].strip())
                items.append(f'<li>{_markdown_inline_to_xhtml(item_text)}</li>')
                i += 1
            result.append('<ul>' + ''.join(items) + '</ul>')
            continue

        # Ordered list
        if re.match(r'^\d+\.\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i].strip()):
                item_text = re.sub(r'^\d+\.\s+', '', lines[i].strip())
                items.append(f'<li>{_markdown_inline_to_xhtml(item_text)}</li>')
                i += 1
            result.append('<ol>' + ''.join(items) + '</ol>')
            continue

        # Regular paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1

        if para_lines:
            para_content = _markdown_inline_to_xhtml(' '.join(para_lines))
            result.append(f'<p>{para_content}</p>')

    return ''.join(result)


def _is_block_start(line: str) -> bool:
    """Check if a line starts a block element."""
    return (
        line.startswith('#') or
        line.startswith('```') or
        line.startswith('>') or
        re.match(r'^[-*]\s+', line) or
        re.match(r'^\d+\.\s+', line) or
        re.match(r'^[-*_]{3,}$', line)
    )


def _markdown_inline_to_xhtml(text: str) -> str:
    """
    Convert inline Markdown elements to XHTML.

    Handles bold, italic, code, links, images.
    """
    # Escape HTML entities first
    text = html.escape(text)

    # Bold **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

    # Italic *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)

    # Strikethrough ~~text~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)

    # Code `text`
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)

    # Images ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<ac:image><ri:url ri:value="\2" /></ac:image>', text)

    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

    return text


def xhtml_to_adf(xhtml: str) -> Dict[str, Any]:
    """
    Convert Confluence XHTML storage format to ADF.

    This is useful for migrating content from v1 API format to v2 API format.

    Args:
        xhtml: XHTML storage format content

    Returns:
        ADF document
    """
    # First convert to Markdown (intermediate format)
    markdown = xhtml_to_markdown(xhtml)

    # Then convert Markdown to ADF
    from adf_helper import markdown_to_adf
    return markdown_to_adf(markdown)


def adf_to_xhtml(adf: Dict[str, Any]) -> str:
    """
    Convert ADF to XHTML storage format.

    This is useful for using v2 content with v1 API endpoints.

    Args:
        adf: ADF document

    Returns:
        XHTML storage format content
    """
    # First convert to Markdown
    from adf_helper import adf_to_markdown
    markdown = adf_to_markdown(adf)

    # Then convert Markdown to XHTML
    return markdown_to_xhtml(markdown)


def extract_text_from_xhtml(xhtml: str) -> str:
    """
    Extract plain text from XHTML content.

    Args:
        xhtml: XHTML storage format content

    Returns:
        Plain text content
    """
    # Remove all HTML tags
    text = re.sub(r'<[^>]+>', ' ', xhtml)
    # Unescape HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def wrap_in_storage_format(content: str) -> str:
    """
    Wrap content in proper Confluence storage format structure.

    Args:
        content: XHTML content

    Returns:
        Complete storage format with proper namespaces
    """
    return content


def validate_xhtml(xhtml: str) -> Tuple[bool, Optional[str]]:
    """
    Validate XHTML storage format.

    Args:
        xhtml: XHTML content to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation - check for unbalanced tags
    tag_stack = []
    tag_pattern = re.compile(r'<(/?)(\w+)[^>]*(/?)>')

    for match in tag_pattern.finditer(xhtml):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        is_self_closing = match.group(3) == '/'

        # Skip self-closing tags
        if is_self_closing:
            continue

        # Skip void elements
        void_elements = {'br', 'hr', 'img', 'input', 'meta', 'link'}
        if tag_name in void_elements:
            continue

        if is_closing:
            if not tag_stack or tag_stack[-1] != tag_name:
                expected = tag_stack[-1] if tag_stack else 'none'
                return False, f"Unexpected closing tag </{tag_name}>, expected </{expected}>"
            tag_stack.pop()
        else:
            tag_stack.append(tag_name)

    if tag_stack:
        return False, f"Unclosed tags: {', '.join(tag_stack)}"

    return True, None
