"""
Shared fixtures for confluence-page live integration tests.
Imports fixtures from shared conftest and adds skill-specific ones.

Uses environment variables: CONFLUENCE_API_TOKEN, CONFLUENCE_EMAIL, CONFLUENCE_SITE_URL
"""

import contextlib
import uuid

import pytest

from confluence_as import (
    get_confluence_client,
)


@pytest.fixture(scope="session")
def confluence_client(request):
    return get_confluence_client()


@pytest.fixture(scope="session")
def test_space(confluence_client):
    spaces = confluence_client.get("/api/v2/spaces", params={"limit": 1})
    if not spaces.get("results"):
        pytest.skip("No spaces available")
    return spaces["results"][0]


@pytest.fixture
def test_page(confluence_client, test_space):
    page = confluence_client.post(
        "/api/v2/pages",
        json_data={
            "spaceId": test_space["id"],
            "status": "current",
            "title": f"Test Page {uuid.uuid4().hex[:8]}",
            "body": {"representation": "storage", "value": "<p>Test.</p>"},
        },
    )
    yield page
    with contextlib.suppress(Exception):
        confluence_client.delete(f"/api/v2/pages/{page['id']}")


@pytest.fixture
def current_user(confluence_client):
    return confluence_client.get("/rest/api/user/current")
