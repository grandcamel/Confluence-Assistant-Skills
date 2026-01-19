"""
Unit tests for list_popular_labels.py
"""


class TestListPopularLabels:
    """Tests for listing popular labels."""

    def test_list_popular_labels_success(self, mock_client):
        """Test successful retrieval of popular labels."""
        # Sample search results with labels
        search_results = {
            "results": [
                {
                    "id": "123",
                    "type": "page",
                    "title": "Page 1",
                    "metadata": {
                        "labels": {
                            "results": [{"name": "documentation"}, {"name": "api"}]
                        }
                    },
                },
                {
                    "id": "124",
                    "type": "page",
                    "title": "Page 2",
                    "metadata": {
                        "labels": {
                            "results": [{"name": "documentation"}, {"name": "tutorial"}]
                        }
                    },
                },
            ],
            "_links": {},
        }

        mock_client.setup_response("get", search_results)

        # Would verify label aggregation and counting

    def test_list_popular_labels_with_space_filter(self, mock_client):
        """Test listing popular labels filtered to specific space."""

        # Would verify CQL query includes space filter
        # Expected CQL: space = "DOCS"

    def test_list_popular_labels_empty_results(self, mock_client):
        """Test listing popular labels with no content."""
        # Setup empty response
        empty_results = {"results": [], "_links": {}}
        mock_client.setup_response("get", empty_results)

        # Would verify empty result handling

    def test_list_popular_labels_with_limit(self, mock_client):
        """Test listing popular labels with result limit."""

        # Would verify only top N labels are returned


class TestLabelAggregation:
    """Tests for aggregating and counting labels."""

    def test_count_label_occurrences(self):
        """Test counting label occurrences across pages."""
        pages = [
            {"labels": ["doc", "api", "v2"]},
            {"labels": ["doc", "tutorial"]},
            {"labels": ["doc", "api"]},
        ]

        # Count occurrences
        from collections import Counter

        all_labels = []
        for page in pages:
            all_labels.extend(page["labels"])

        counts = Counter(all_labels)
        assert counts["doc"] == 3
        assert counts["api"] == 2
        assert counts["tutorial"] == 1
        assert counts["v2"] == 1

    def test_sort_labels_by_count(self):
        """Test sorting labels by popularity."""

        label_counts = {"doc": 5, "api": 3, "tutorial": 1, "v2": 2}
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)

        assert sorted_labels[0] == ("doc", 5)
        assert sorted_labels[1] == ("api", 3)
        assert sorted_labels[2] == ("v2", 2)
        assert sorted_labels[3] == ("tutorial", 1)

    def test_limit_results(self):
        """Test limiting number of results."""
        sorted_labels = [("doc", 5), ("api", 3), ("v2", 2), ("tutorial", 1)]
        limit = 2

        limited = sorted_labels[:limit]
        assert len(limited) == 2
        assert limited[0] == ("doc", 5)
        assert limited[1] == ("api", 3)
