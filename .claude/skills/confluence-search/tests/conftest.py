"""
Pytest fixtures for confluence-search skill tests.

Extends the shared fixtures with search-specific test data.
"""

import pytest
import sys
from pathlib import Path

# Add shared lib to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'shared' / 'scripts' / 'lib'))

# Import shared conftest to get all its fixtures
# This makes mock_client, sample_page, sample_search_results, etc. available
shared_conftest_path = Path(__file__).parent.parent.parent / 'shared' / 'tests' / 'conftest.py'
if shared_conftest_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("shared_conftest", shared_conftest_path)
    shared_conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared_conftest)

    # Make shared fixtures available
    globals().update({
        name: getattr(shared_conftest, name)
        for name in dir(shared_conftest)
        if name.startswith('pytest_') or (hasattr(getattr(shared_conftest, name), '__name__') and
           getattr(getattr(shared_conftest, name), '_pytestfixturefunction', None))
    })


@pytest.fixture
def sample_cql_fields():
    """Sample CQL field suggestions."""
    return [
        {"name": "space", "type": "string", "description": "Space key"},
        {"name": "title", "type": "string", "description": "Page title"},
        {"name": "text", "type": "string", "description": "Full text search"},
        {"name": "type", "type": "enum", "description": "Content type",
         "values": ["page", "blogpost", "comment", "attachment"]},
        {"name": "label", "type": "string", "description": "Content label"},
        {"name": "creator", "type": "string", "description": "Content creator"},
        {"name": "created", "type": "date", "description": "Creation date"},
        {"name": "lastModified", "type": "date", "description": "Last modified date"},
        {"name": "ancestor", "type": "string", "description": "Ancestor page ID"},
        {"name": "parent", "type": "string", "description": "Parent page ID"},
    ]


@pytest.fixture
def sample_cql_operators():
    """Sample CQL operators."""
    return [
        {"operator": "=", "description": "Equals"},
        {"operator": "!=", "description": "Not equals"},
        {"operator": "~", "description": "Contains (text search)"},
        {"operator": "!~", "description": "Does not contain"},
        {"operator": ">", "description": "Greater than"},
        {"operator": "<", "description": "Less than"},
        {"operator": ">=", "description": "Greater than or equal"},
        {"operator": "<=", "description": "Less than or equal"},
        {"operator": "in", "description": "In list"},
        {"operator": "not in", "description": "Not in list"},
    ]


@pytest.fixture
def sample_cql_functions():
    """Sample CQL functions."""
    return [
        {"name": "currentUser()", "description": "Current logged in user"},
        {"name": "startOfDay()", "description": "Start of today"},
        {"name": "startOfWeek()", "description": "Start of this week"},
        {"name": "startOfMonth()", "description": "Start of this month"},
        {"name": "startOfYear()", "description": "Start of this year"},
        {"name": "endOfDay()", "description": "End of today"},
        {"name": "endOfWeek()", "description": "End of this week"},
        {"name": "endOfMonth()", "description": "End of this month"},
        {"name": "endOfYear()", "description": "End of this year"},
    ]


@pytest.fixture
def sample_query_history():
    """Sample query history entries."""
    return [
        {
            "query": "space = 'DOCS' AND type = page",
            "timestamp": "2024-01-15T10:30:00.000Z",
            "results_count": 42
        },
        {
            "query": "label = 'api' AND creator = currentUser()",
            "timestamp": "2024-01-14T15:45:00.000Z",
            "results_count": 15
        },
        {
            "query": "text ~ 'documentation' ORDER BY lastModified DESC",
            "timestamp": "2024-01-13T09:20:00.000Z",
            "results_count": 128
        },
    ]


@pytest.fixture
def sample_spaces_for_suggestion():
    """Sample spaces for field value suggestions."""
    return {
        "results": [
            {"id": "1", "key": "DOCS", "name": "Documentation"},
            {"id": "2", "key": "KB", "name": "Knowledge Base"},
            {"id": "3", "key": "DEV", "name": "Development"},
        ]
    }


@pytest.fixture
def sample_labels_for_suggestion():
    """Sample labels for field value suggestions."""
    return {
        "results": [
            {"id": "1", "name": "documentation", "prefix": "global"},
            {"id": "2", "name": "api", "prefix": "global"},
            {"id": "3", "name": "tutorial", "prefix": "global"},
            {"id": "4", "name": "reference", "prefix": "global"},
        ]
    }
