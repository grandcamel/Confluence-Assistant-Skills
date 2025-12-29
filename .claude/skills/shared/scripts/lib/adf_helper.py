"""
Atlassian Document Format (ADF) Helper

Provides utilities for working with ADF, the JSON-based document format
used by Confluence Cloud API v2.

Features:
- Convert plain text to ADF
- Convert Markdown to ADF
- Convert ADF to plain text
- Convert ADF to Markdown

ADF Documentation:
https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/

Usage:
    from adf_helper import text_to_adf, markdown_to_adf, adf_to_text

    # Create ADF from text
    adf = text_to_adf("Hello, world!")

    # Create ADF from Markdown
    adf = markdown_to_adf("# Heading\n\nParagraph with **bold** text.")

    # Convert ADF back to text
    text = adf_to_text(adf)
"""

import re
import json
from typing import Any, Dict, List, Optional, Union


def create_adf_doc(content: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create an ADF document wrapper.

    Args:
        content: List of ADF block nodes

    Returns:
        Complete ADF document
    """
    return {
        "type": "doc",
        "version": 1,
        "content": content
    }


def create_paragraph(content: List[Dict[str, Any]] = None, text: str = None) -> Dict[str, Any]:
    """
    Create an ADF paragraph node.

    Args:
        content: List of inline nodes (text, marks, etc.)
        text: Simple text content (creates a text node automatically)

    Returns:
        ADF paragraph node
    """
    if text is not None:
        content = [create_text(text)]
    elif content is None:
        content = []

    return {
        "type": "paragraph",
        "content": content
    }


def create_text(text: str, marks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an ADF text node.

    Args:
        text: The text content
        marks: List of marks (bold, italic, link, etc.)

    Returns:
        ADF text node
    """
    node = {
        "type": "text",
        "text": text
    }
    if marks:
        node["marks"] = marks
    return node


def create_heading(text: str, level: int = 1) -> Dict[str, Any]:
    """
    Create an ADF heading node.

    Args:
        text: Heading text
        level: Heading level (1-6)

    Returns:
        ADF heading node
    """
    level = max(1, min(6, level))
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [create_text(text)]
    }


def create_bullet_list(items: List[str]) -> Dict[str, Any]:
    """
    Create an ADF bullet list.

    Args:
        items: List of text items

    Returns:
        ADF bulletList node
    """
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [create_paragraph(text=item)]
            }
            for item in items
        ]
    }


def create_ordered_list(items: List[str], start: int = 1) -> Dict[str, Any]:
    """
    Create an ADF ordered list.

    Args:
        items: List of text items
        start: Starting number

    Returns:
        ADF orderedList node
    """
    return {
        "type": "orderedList",
        "attrs": {"order": start},
        "content": [
            {
                "type": "listItem",
                "content": [create_paragraph(text=item)]
            }
            for item in items
        ]
    }


def create_code_block(code: str, language: str = None) -> Dict[str, Any]:
    """
    Create an ADF code block.

    Args:
        code: Code content
        language: Programming language for syntax highlighting

    Returns:
        ADF codeBlock node
    """
    node = {
        "type": "codeBlock",
        "content": [create_text(code)]
    }
    if language:
        node["attrs"] = {"language": language}
    return node


def create_blockquote(text: str) -> Dict[str, Any]:
    """
    Create an ADF blockquote.

    Args:
        text: Quote text

    Returns:
        ADF blockquote node
    """
    return {
        "type": "blockquote",
        "content": [create_paragraph(text=text)]
    }


def create_rule() -> Dict[str, Any]:
    """
    Create an ADF horizontal rule.

    Returns:
        ADF rule node
    """
    return {"type": "rule"}


def create_table(rows: List[List[str]], header: bool = True) -> Dict[str, Any]:
    """
    Create an ADF table.

    Args:
        rows: List of rows, each row is a list of cell contents
        header: If True, first row is treated as header

    Returns:
        ADF table node
    """
    table_rows = []

    for i, row in enumerate(rows):
        cells = []
        cell_type = "tableHeader" if (header and i == 0) else "tableCell"

        for cell_text in row:
            cells.append({
                "type": cell_type,
                "content": [create_paragraph(text=str(cell_text))]
            })

        table_rows.append({
            "type": "tableRow",
            "content": cells
        })

    return {
        "type": "table",
        "content": table_rows
    }


def create_link(text: str, url: str) -> Dict[str, Any]:
    """
    Create an ADF text node with link mark.

    Args:
        text: Link text
        url: Link URL

    Returns:
        ADF text node with link mark
    """
    return create_text(text, marks=[{
        "type": "link",
        "attrs": {"href": url}
    }])


def text_to_adf(text: str) -> Dict[str, Any]:
    """
    Convert plain text to ADF.

    Handles:
    - Paragraph breaks (double newlines)
    - Preserves single line breaks within paragraphs

    Args:
        text: Plain text content

    Returns:
        ADF document
    """
    if not text:
        return create_adf_doc([create_paragraph(text="")])

    # Split on double newlines for paragraphs
    paragraphs = re.split(r'\n\n+', text.strip())
    content = []

    for para in paragraphs:
        if para.strip():
            content.append(create_paragraph(text=para.strip()))

    return create_adf_doc(content if content else [create_paragraph(text="")])


def markdown_to_adf(markdown: str) -> Dict[str, Any]:
    """
    Convert Markdown to ADF.

    Supports:
    - Headings (# to ######)
    - Bold (**text** or __text__)
    - Italic (*text* or _text_)
    - Code (`code` and code blocks)
    - Links [text](url)
    - Bullet lists (- or *)
    - Ordered lists (1. 2. etc.)
    - Blockquotes (>)
    - Horizontal rules (---)

    Args:
        markdown: Markdown content

    Returns:
        ADF document
    """
    if not markdown:
        return create_adf_doc([create_paragraph(text="")])

    content = []
    lines = markdown.split('\n')
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
            text = heading_match.group(2)
            content.append(create_heading(text, level))
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}$', stripped):
            content.append(create_rule())
            i += 1
            continue

        # Code block (fenced)
        if stripped.startswith('```'):
            lang_match = re.match(r'^```(\w*)$', stripped)
            language = lang_match.group(1) if lang_match else None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            content.append(create_code_block('\n'.join(code_lines), language))
            i += 1  # Skip closing ```
            continue

        # Blockquote
        if stripped.startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote_text = re.sub(r'^>\s*', '', lines[i].strip())
                quote_lines.append(quote_text)
                i += 1
            content.append(create_blockquote('\n'.join(quote_lines)))
            continue

        # Bullet list
        if re.match(r'^[-*]\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^[-*]\s+', lines[i].strip()):
                item_text = re.sub(r'^[-*]\s+', '', lines[i].strip())
                items.append(item_text)
                i += 1
            content.append(create_bullet_list(items))
            continue

        # Ordered list
        if re.match(r'^\d+\.\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i].strip()):
                item_text = re.sub(r'^\d+\.\s+', '', lines[i].strip())
                items.append(item_text)
                i += 1
            content.append(create_ordered_list(items))
            continue

        # Regular paragraph - collect consecutive non-empty lines
        para_lines = []
        while i < len(lines) and lines[i].strip() and not _is_block_element(lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1

        if para_lines:
            para_text = ' '.join(para_lines)
            para_content = _parse_inline_markdown(para_text)
            content.append({
                "type": "paragraph",
                "content": para_content
            })

    return create_adf_doc(content if content else [create_paragraph(text="")])


def _is_block_element(line: str) -> bool:
    """Check if a line starts a block element."""
    return (
        line.startswith('#') or
        line.startswith('```') or
        line.startswith('>') or
        re.match(r'^[-*]\s+', line) or
        re.match(r'^\d+\.\s+', line) or
        re.match(r'^[-*_]{3,}$', line)
    )


def _parse_inline_markdown(text: str) -> List[Dict[str, Any]]:
    """
    Parse inline Markdown elements (bold, italic, code, links).

    Args:
        text: Text with inline Markdown

    Returns:
        List of ADF inline nodes
    """
    nodes = []
    remaining = text

    # Pattern for inline elements
    pattern = r'(\*\*(.+?)\*\*)|(__(.+?)__)|(\*(.+?)\*)|(_(.+?)_)|(`(.+?)`)|(\[([^\]]+)\]\(([^)]+)\))'

    last_end = 0
    for match in re.finditer(pattern, text):
        # Add text before match
        if match.start() > last_end:
            nodes.append(create_text(text[last_end:match.start()]))

        # Bold **text**
        if match.group(2):
            nodes.append(create_text(match.group(2), marks=[{"type": "strong"}]))
        # Bold __text__
        elif match.group(4):
            nodes.append(create_text(match.group(4), marks=[{"type": "strong"}]))
        # Italic *text*
        elif match.group(6):
            nodes.append(create_text(match.group(6), marks=[{"type": "em"}]))
        # Italic _text_
        elif match.group(8):
            nodes.append(create_text(match.group(8), marks=[{"type": "em"}]))
        # Code `text`
        elif match.group(10):
            nodes.append(create_text(match.group(10), marks=[{"type": "code"}]))
        # Link [text](url)
        elif match.group(12):
            nodes.append(create_link(match.group(12), match.group(13)))

        last_end = match.end()

    # Add remaining text
    if last_end < len(text):
        nodes.append(create_text(text[last_end:]))

    # If no inline elements found, just return the text
    if not nodes:
        nodes = [create_text(text)]

    return nodes


def adf_to_text(adf: Dict[str, Any]) -> str:
    """
    Convert ADF to plain text.

    Args:
        adf: ADF document

    Returns:
        Plain text content
    """
    if not adf:
        return ""

    def extract_text(node: Dict[str, Any]) -> str:
        """Recursively extract text from a node."""
        if node.get("type") == "text":
            return node.get("text", "")

        content = node.get("content", [])
        if not content:
            return ""

        texts = []
        for child in content:
            child_text = extract_text(child)
            if child_text:
                texts.append(child_text)

        node_type = node.get("type", "")

        if node_type == "paragraph":
            return "".join(texts)
        elif node_type == "heading":
            return "".join(texts)
        elif node_type == "bulletList" or node_type == "orderedList":
            return "\n".join(f"- {t}" for t in texts)
        elif node_type == "listItem":
            return "".join(texts)
        elif node_type == "codeBlock":
            return "".join(texts)
        elif node_type == "blockquote":
            return "> " + "".join(texts)
        elif node_type == "table":
            return "\n".join(texts)
        elif node_type == "tableRow":
            return " | ".join(texts)
        elif node_type in ("tableCell", "tableHeader"):
            return "".join(texts)
        elif node_type == "hardBreak":
            return "\n"
        elif node_type == "rule":
            return "---"
        else:
            return "".join(texts)

    lines = []
    for node in adf.get("content", []):
        text = extract_text(node)
        if text:
            lines.append(text)

    return "\n\n".join(lines)


def adf_to_markdown(adf: Dict[str, Any]) -> str:
    """
    Convert ADF to Markdown.

    Args:
        adf: ADF document

    Returns:
        Markdown content
    """
    if not adf:
        return ""

    def convert_node(node: Dict[str, Any], indent: str = "") -> str:
        """Convert a single ADF node to Markdown."""
        node_type = node.get("type", "")
        content = node.get("content", [])
        attrs = node.get("attrs", {})

        if node_type == "text":
            text = node.get("text", "")
            marks = node.get("marks", [])

            for mark in marks:
                mark_type = mark.get("type", "")
                if mark_type == "strong":
                    text = f"**{text}**"
                elif mark_type == "em":
                    text = f"*{text}*"
                elif mark_type == "code":
                    text = f"`{text}`"
                elif mark_type == "link":
                    url = mark.get("attrs", {}).get("href", "")
                    text = f"[{text}]({url})"
                elif mark_type == "strike":
                    text = f"~~{text}~~"

            return text

        elif node_type == "paragraph":
            return "".join(convert_node(c) for c in content)

        elif node_type == "heading":
            level = attrs.get("level", 1)
            text = "".join(convert_node(c) for c in content)
            return "#" * level + " " + text

        elif node_type == "bulletList":
            items = []
            for item in content:
                item_text = convert_node(item, indent + "  ")
                items.append(f"{indent}- {item_text}")
            return "\n".join(items)

        elif node_type == "orderedList":
            items = []
            start = attrs.get("order", 1)
            for i, item in enumerate(content):
                item_text = convert_node(item, indent + "   ")
                items.append(f"{indent}{start + i}. {item_text}")
            return "\n".join(items)

        elif node_type == "listItem":
            return "".join(convert_node(c, indent) for c in content)

        elif node_type == "codeBlock":
            language = attrs.get("language", "")
            code = "".join(convert_node(c) for c in content)
            return f"```{language}\n{code}\n```"

        elif node_type == "blockquote":
            text = "".join(convert_node(c) for c in content)
            lines = text.split("\n")
            return "\n".join(f"> {line}" for line in lines)

        elif node_type == "rule":
            return "---"

        elif node_type == "table":
            rows = []
            for row_node in content:
                row = convert_node(row_node)
                rows.append(row)
            if rows:
                # Add header separator after first row
                first_row_cells = content[0].get("content", []) if content else []
                separator = "| " + " | ".join(["---"] * len(first_row_cells)) + " |"
                rows.insert(1, separator)
            return "\n".join(rows)

        elif node_type == "tableRow":
            cells = [convert_node(c) for c in content]
            return "| " + " | ".join(cells) + " |"

        elif node_type in ("tableCell", "tableHeader"):
            return "".join(convert_node(c) for c in content)

        elif node_type == "hardBreak":
            return "  \n"

        else:
            return "".join(convert_node(c, indent) for c in content)

    blocks = []
    for node in adf.get("content", []):
        block = convert_node(node)
        if block:
            blocks.append(block)

    return "\n\n".join(blocks)


def validate_adf(adf: Dict[str, Any]) -> bool:
    """
    Validate basic ADF structure.

    Args:
        adf: ADF document to validate

    Returns:
        True if valid

    Raises:
        ValueError: If invalid
    """
    if not isinstance(adf, dict):
        raise ValueError("ADF must be a dictionary")

    if adf.get("type") != "doc":
        raise ValueError("ADF must have type 'doc'")

    if "content" not in adf:
        raise ValueError("ADF must have 'content' array")

    if not isinstance(adf["content"], list):
        raise ValueError("ADF content must be a list")

    return True
