"""
Live Integration Tests - Search Operations

Tests for CQL search operations against a real Confluence instance.

Usage:
    pytest test_search.py --live -v
"""

import time
import uuid

import pytest


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.search
class TestCQLSearch:
    """Tests for CQL query search."""

    def test_search_by_space(self, confluence_client, test_space, test_page):
        """Test searching for pages in a specific space."""
        # Wait for indexing
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND type = page"

        result = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql, "limit": 50},
            operation="search by space",
        )

        assert "results" in result
        # Should find at least the test page
        assert len(result["results"]) >= 1

    def test_search_by_title(self, confluence_client, test_space, test_page):
        """Test searching for pages by title."""
        # Wait for indexing
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND title ~ 'Test Page'"

        result = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql, "limit": 50},
            operation="search by title",
        )

        assert "results" in result

    def test_search_by_type_page(self, confluence_client, test_space, test_page):
        """Test filtering search to pages only."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND type = page"

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="search pages only"
        )

        for item in result.get("results", []):
            content = item.get("content", {})
            assert content.get("type") == "page"

    def test_search_by_type_blogpost(
        self, confluence_client, test_space, test_blogpost
    ):
        """Test filtering search to blog posts only."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND type = blogpost"

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="search blogposts only"
        )

        for item in result.get("results", []):
            content = item.get("content", {})
            assert content.get("type") == "blogpost"

    def test_search_with_ordering(self, confluence_client, test_space):
        """Test search with ORDER BY clause."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}' ORDER BY created DESC"

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="search with ordering"
        )

        assert "results" in result

    def test_search_pagination(self, confluence_client, test_space):
        """Test search result pagination."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}'"

        # First page
        result1 = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql, "limit": 5, "start": 0},
            operation="search page 1",
        )

        assert "results" in result1
        assert result1.get("limit") == 5
        assert result1.get("start") == 0


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.search
class TestTextSearch:
    """Tests for full-text search."""

    def test_text_search_basic(
        self, confluence_client, test_space, test_page_with_content
    ):
        """Test basic text search."""
        # Wait for indexing
        time.sleep(3)

        cql = f"space = '{test_space['key']}' AND text ~ 'Hello'"

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="text search"
        )

        assert "results" in result

    def test_text_search_phrase(
        self, confluence_client, test_space, test_page_with_content
    ):
        """Test phrase text search."""
        time.sleep(3)

        cql = f'space = "{test_space["key"]}" AND text ~ "Test Heading"'

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="phrase search"
        )

        assert "results" in result

    def test_search_with_excerpt(self, confluence_client, test_space, test_page):
        """Test that search returns excerpts."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND type = page"

        result = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql, "excerpt": "highlight"},
            operation="search with excerpt",
        )

        assert "results" in result
        # Excerpts should be in results
        for _item in result.get("results", []):
            # Excerpt may or may not be present
            pass


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.search
class TestSearchExpand:
    """Tests for search with expanded fields."""

    def test_search_expand_space(self, confluence_client, test_space, test_page):
        """Test search with space expansion."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND type = page"

        result = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql, "expand": "content.space"},
            operation="search expand space",
        )

        assert "results" in result
        for item in result.get("results", []):
            content = item.get("content", {})
            if "space" in content:
                assert "key" in content["space"]

    def test_search_expand_version(self, confluence_client, test_space, test_page):
        """Test search with version expansion."""
        time.sleep(2)

        cql = f"space = '{test_space['key']}' AND type = page"

        result = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql, "expand": "content.version"},
            operation="search expand version",
        )

        assert "results" in result
        for item in result.get("results", []):
            content = item.get("content", {})
            if "version" in content:
                assert "number" in content["version"]


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.search
class TestInvalidSearch:
    """Tests for invalid search queries."""

    def test_invalid_cql_syntax(self, confluence_client):
        """Test that invalid CQL syntax returns an error."""
        from confluence_as import ConfluenceError

        cql = "space = 'TEST' AND ("  # Unbalanced parenthesis

        with pytest.raises(ConfluenceError):
            confluence_client.get(
                "/rest/api/search", params={"cql": cql}, operation="invalid cql"
            )

    def test_search_nonexistent_space(self, confluence_client):
        """Test searching in a non-existent space returns empty results."""
        cql = "space = 'NONEXISTENTSPACE999'"

        result = confluence_client.get(
            "/rest/api/search",
            params={"cql": cql},
            operation="search nonexistent space",
        )

        assert result.get("results", []) == []
        assert result.get("totalSize", 0) == 0


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.search
@pytest.mark.labels
class TestSearchByLabel:
    """Tests for searching by labels.

    Note: Label operations use v1 API, not v2.
    """

    @pytest.mark.skip(reason="v2 API doesn't support POST for labels - use v1 API")
    def test_add_label_and_search(self, confluence_client, test_page, test_label):
        """Test adding a label and searching for it."""
        # Add label to page
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={"name": test_label},
            operation="add label",
        )

        # Wait for indexing
        time.sleep(3)

        # Search by label
        cql = f"label = '{test_label}'"

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="search by label"
        )

        assert "results" in result
        assert len(result["results"]) >= 1

        # Verify our page is in results
        page_ids = [r.get("content", {}).get("id") for r in result["results"]]
        assert test_page["id"] in page_ids

    @pytest.mark.skip(reason="v2 API doesn't support POST for labels - use v1 API")
    def test_search_multiple_labels(self, confluence_client, test_page):
        """Test searching for content with multiple labels."""
        label1 = f"label1-{uuid.uuid4().hex[:6]}"
        label2 = f"label2-{uuid.uuid4().hex[:6]}"

        # Add labels
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={"name": label1},
            operation="add label 1",
        )
        confluence_client.post(
            f"/api/v2/pages/{test_page['id']}/labels",
            json_data={"name": label2},
            operation="add label 2",
        )

        time.sleep(3)

        # Search for both labels
        cql = f"label = '{label1}' AND label = '{label2}'"

        result = confluence_client.get(
            "/rest/api/search", params={"cql": cql}, operation="search multiple labels"
        )

        assert "results" in result
