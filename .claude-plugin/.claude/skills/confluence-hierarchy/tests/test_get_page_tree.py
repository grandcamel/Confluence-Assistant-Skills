"""
Unit tests for get_page_tree.py
"""

import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestGetPageTree:
    """Tests for getting full page tree."""

    def test_build_tree_structure(self, sample_page, sample_children):
        """Test building hierarchical tree structure."""
        # Root page
        root = sample_page.copy()
        root["children"] = sample_children["results"]

        assert "children" in root
        assert len(root["children"]) == 2

    def test_tree_with_nested_children(self, sample_page_tree):
        """Test tree with multiple levels."""
        tree = sample_page_tree

        # Verify root
        assert tree["id"] == "123456"
        assert tree["title"] == "Root Page"

        # Verify children
        assert len(tree["children"]) == 2
        assert tree["children"][0]["title"] == "Child 1"

        # Verify grandchildren
        assert len(tree["children"][0]["children"]) == 1
        assert tree["children"][0]["children"][0]["title"] == "Grandchild 1"

    def test_tree_max_depth_limit(self, sample_page_tree):
        """Test limiting tree depth."""

        def limit_tree_depth(node, max_depth, current_depth=0):
            if current_depth >= max_depth:
                node["children"] = []
                return node

            if "children" in node:
                node["children"] = [
                    limit_tree_depth(child, max_depth, current_depth + 1)
                    for child in node["children"]
                ]
            return node

        # Limit to depth 1 (only direct children)
        limited_tree = limit_tree_depth(sample_page_tree.copy(), max_depth=1)

        assert len(limited_tree["children"]) == 2
        # Children should have no children (depth limit reached)
        for child in limited_tree["children"]:
            assert len(child["children"]) == 0

    def test_tree_output_text_format(self, sample_page_tree):
        """Test formatting tree as indented text."""

        def format_tree_node(node, depth=0):
            indent = "  " * depth
            lines = [f"{indent}{node['title']} (ID: {node['id']})"]

            for child in node.get("children", []):
                lines.extend(format_tree_node(child, depth + 1))

            return lines

        output_lines = format_tree_node(sample_page_tree)
        output = "\n".join(output_lines)

        assert "Root Page" in output
        assert "  Child 1" in output
        assert "    Grandchild 1" in output

    def test_tree_statistics(self, sample_page_tree):
        """Test calculating tree statistics."""

        def count_nodes(node):
            count = 1  # Count self
            for child in node.get("children", []):
                count += count_nodes(child)
            return count

        def max_depth(node, current_depth=0):
            if not node.get("children"):
                return current_depth
            return max(
                max_depth(child, current_depth + 1) for child in node["children"]
            )

        total_pages = count_nodes(sample_page_tree)
        tree_depth = max_depth(sample_page_tree)

        assert total_pages == 4  # Root + 2 children + 1 grandchild
        assert tree_depth == 2  # 0=root, 1=children, 2=grandchildren

    def test_tree_to_flat_list(self, sample_page_tree):
        """Test converting tree to flat list."""

        def flatten_tree(node, depth=0):
            items = [{"id": node["id"], "title": node["title"], "depth": depth}]

            for child in node.get("children", []):
                items.extend(flatten_tree(child, depth + 1))

            return items

        flat_list = flatten_tree(sample_page_tree)

        assert len(flat_list) == 4
        assert flat_list[0]["depth"] == 0  # Root
        assert flat_list[1]["depth"] == 1  # Child 1
        assert flat_list[2]["depth"] == 2  # Grandchild 1
        assert flat_list[3]["depth"] == 1  # Child 2

    def test_empty_tree(self, sample_page):
        """Test tree with no children."""
        page = sample_page.copy()
        page["children"] = []

        assert "children" in page
        assert len(page["children"]) == 0

    def test_tree_json_output(self, sample_page_tree):
        """Test JSON output of tree."""
        import json

        json_output = json.dumps(sample_page_tree, indent=2)

        assert "Root Page" in json_output
        assert "children" in json_output
        assert "Grandchild 1" in json_output
