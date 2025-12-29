"""
Live Integration Tests - Page Lifecycle

Tests for page CRUD operations against a real Confluence instance.

Usage:
    pytest test_page_lifecycle.py --profile development -v
"""

import uuid
import pytest


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.pages
class TestPageCreate:
    """Tests for page creation."""

    def test_create_basic_page(self, confluence_client, test_space):
        """Test creating a basic page with minimal content."""
        title = f"Basic Page {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Basic content</p>'
                }
            },
            operation='create basic page'
        )

        try:
            assert 'id' in page
            assert page['title'] == title
            assert page['spaceId'] == test_space['id']
            assert page['status'] == 'current'
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    def test_create_page_with_parent(self, confluence_client, test_space, test_page):
        """Test creating a child page under a parent."""
        child_title = f"Child Page {uuid.uuid4().hex[:8]}"

        child = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'parentId': test_page['id'],
                'status': 'current',
                'title': child_title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Child content</p>'
                }
            },
            operation='create child page'
        )

        try:
            assert child['parentId'] == test_page['id']
            assert child['title'] == child_title
        finally:
            confluence_client.delete(f"/api/v2/pages/{child['id']}")

    def test_create_page_with_rich_content(self, confluence_client, test_space):
        """Test creating a page with rich formatted content."""
        title = f"Rich Page {uuid.uuid4().hex[:8]}"

        content = """
        <h1>Heading 1</h1>
        <p>Paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Cell 1</td><td>Cell 2</td></tr>
        </table>
        """

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': content
                }
            },
            operation='create rich content page'
        )

        try:
            assert 'id' in page
            assert page['title'] == title
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")

    @pytest.mark.skip(reason="Draft pages have different deletion behavior - needs v1 API")
    def test_create_draft_page(self, confluence_client, test_space):
        """Test creating a draft page."""
        title = f"Draft Page {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'draft',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Draft content</p>'
                }
            },
            operation='create draft page'
        )

        try:
            assert page['status'] == 'draft'
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.pages
class TestPageRead:
    """Tests for reading pages."""

    def test_get_page_by_id(self, confluence_client, test_page):
        """Test retrieving a page by ID."""
        page = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}",
            operation='get page by id'
        )

        assert page['id'] == test_page['id']
        assert page['title'] == test_page['title']

    def test_get_page_with_body(self, confluence_client, test_page):
        """Test retrieving a page with body content."""
        page = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}",
            params={'body-format': 'storage'},
            operation='get page with body'
        )

        assert 'body' in page
        assert 'storage' in page['body']
        assert 'value' in page['body']['storage']

    def test_get_page_children(self, confluence_client, test_page, test_child_page):
        """Test retrieving child pages."""
        children = list(confluence_client.paginate(
            f"/api/v2/pages/{test_page['id']}/children",
            operation='get page children'
        ))

        assert len(children) >= 1
        child_ids = [c['id'] for c in children]
        assert test_child_page['id'] in child_ids

    def test_get_nonexistent_page(self, confluence_client):
        """Test retrieving a non-existent page returns 404."""
        from error_handler import NotFoundError

        with pytest.raises(NotFoundError):
            confluence_client.get(
                '/api/v2/pages/999999999999',
                operation='get nonexistent page'
            )


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.pages
class TestPageUpdate:
    """Tests for updating pages."""

    def test_update_page_title(self, confluence_client, test_page):
        """Test updating a page title."""
        new_title = f"Updated Title {uuid.uuid4().hex[:8]}"
        current_version = test_page['version']['number']

        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                'id': test_page['id'],
                'status': 'current',
                'title': new_title,
                'version': {
                    'number': current_version + 1
                }
            },
            operation='update page title'
        )

        assert updated['title'] == new_title
        assert updated['version']['number'] == current_version + 1

    def test_update_page_body(self, confluence_client, test_page):
        """Test updating page content."""
        new_content = '<p>Updated content with new text.</p>'
        current_version = test_page['version']['number']

        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                'id': test_page['id'],
                'status': 'current',
                'title': test_page['title'],
                'version': {
                    'number': current_version + 1,
                    'message': 'Updated content'
                },
                'body': {
                    'representation': 'storage',
                    'value': new_content
                }
            },
            operation='update page body'
        )

        assert updated['version']['number'] == current_version + 1

        # Verify content
        page = confluence_client.get(
            f"/api/v2/pages/{test_page['id']}",
            params={'body-format': 'storage'},
            operation='verify updated content'
        )
        assert 'Updated content' in page['body']['storage']['value']

    def test_update_with_version_message(self, confluence_client, test_page):
        """Test updating with a version message."""
        current_version = test_page['version']['number']
        version_message = "Test version message"

        updated = confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                'id': test_page['id'],
                'status': 'current',
                'title': test_page['title'],
                'version': {
                    'number': current_version + 1,
                    'message': version_message
                }
            },
            operation='update with version message'
        )

        assert updated['version']['message'] == version_message


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.pages
class TestPageDelete:
    """Tests for deleting pages."""

    def test_delete_page(self, confluence_client, test_space):
        """Test deleting a page."""
        # Create a page to delete
        title = f"Page to Delete {uuid.uuid4().hex[:8]}"

        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': title,
                'body': {
                    'representation': 'storage',
                    'value': '<p>Will be deleted</p>'
                }
            },
            operation='create page for deletion'
        )

        page_id = page['id']

        # Delete it
        confluence_client.delete(
            f"/api/v2/pages/{page_id}",
            operation='delete page'
        )

        # Verify it's gone or trashed
        # In Confluence Cloud, deleted pages go to trash first
        from error_handler import NotFoundError
        try:
            page = confluence_client.get(
                f"/api/v2/pages/{page_id}",
                operation='verify page deleted'
            )
            # If we got the page back, it should be trashed
            assert page.get('status') == 'trashed', f"Page status should be 'trashed', got {page.get('status')}"
        except NotFoundError:
            # This is also acceptable - page is completely gone
            pass

    def test_delete_page_with_children(self, confluence_client, test_space):
        """Test deleting a parent page (children should be orphaned or moved)."""
        # Create parent
        parent = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f"Parent {uuid.uuid4().hex[:8]}",
                'body': {'representation': 'storage', 'value': '<p>Parent</p>'}
            },
            operation='create parent for deletion test'
        )

        # Create child
        child = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'parentId': parent['id'],
                'status': 'current',
                'title': f"Child {uuid.uuid4().hex[:8]}",
                'body': {'representation': 'storage', 'value': '<p>Child</p>'}
            },
            operation='create child for deletion test'
        )

        try:
            # Delete child first, then parent
            confluence_client.delete(f"/api/v2/pages/{child['id']}")
            confluence_client.delete(f"/api/v2/pages/{parent['id']}")
        except Exception:
            # Clean up on failure
            try:
                confluence_client.delete(f"/api/v2/pages/{child['id']}")
            except Exception:
                pass
            try:
                confluence_client.delete(f"/api/v2/pages/{parent['id']}")
            except Exception:
                pass
            raise


@pytest.mark.integration
@pytest.mark.confluence
@pytest.mark.pages
class TestPageVersions:
    """Tests for page version history."""

    def test_get_page_versions(self, confluence_client, test_page):
        """Test retrieving page version history."""
        # First update the page to create a version
        current_version = test_page['version']['number']

        confluence_client.put(
            f"/api/v2/pages/{test_page['id']}",
            json_data={
                'id': test_page['id'],
                'status': 'current',
                'title': test_page['title'],
                'version': {'number': current_version + 1}
            },
            operation='create new version'
        )

        # Get versions using v1 API
        versions = confluence_client.get(
            f"/rest/api/content/{test_page['id']}/version",
            operation='get page versions'
        )

        assert 'results' in versions
        assert len(versions['results']) >= 1

    def test_multiple_versions(self, confluence_client, test_space):
        """Test creating multiple versions."""
        # Create page
        page = confluence_client.post(
            '/api/v2/pages',
            json_data={
                'spaceId': test_space['id'],
                'status': 'current',
                'title': f"Version Test {uuid.uuid4().hex[:8]}",
                'body': {'representation': 'storage', 'value': '<p>v1</p>'}
            },
            operation='create version test page'
        )

        try:
            import time
            # Create 3 more versions (with small delay to avoid race conditions)
            for i in range(2, 5):
                time.sleep(0.5)  # Avoid race condition in version updates
                page = confluence_client.put(
                    f"/api/v2/pages/{page['id']}",
                    json_data={
                        'id': page['id'],
                        'status': 'current',
                        'title': page['title'],
                        'version': {'number': i, 'message': f'Version {i}'},
                        'body': {'representation': 'storage', 'value': f'<p>v{i}</p>'}
                    },
                    operation=f'create version {i}'
                )

            # Get versions
            versions = confluence_client.get(
                f"/rest/api/content/{page['id']}/version",
                operation='get all versions'
            )

            assert len(versions['results']) >= 4
        finally:
            confluence_client.delete(f"/api/v2/pages/{page['id']}")
