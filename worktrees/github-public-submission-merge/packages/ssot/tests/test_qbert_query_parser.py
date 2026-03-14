"""
Tests for the Qbert Query Parser.
"""

import pytest
from qube.qbert_query_parser import (
    QbertQueryParser,
    QueryType,
    ParsedQuery,
    create_parser,
)


class TestQbertQueryParser:
    """Test suite for the QbertQueryParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = create_parser()

    def test_capsule_lookup_query(self):
        """Test parsing a capsule lookup query."""
        query = "capsule qube cinematic v1"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.CAPSULE_LOOKUP
        assert result.filters is not None
        assert result.filters.get("version") == "v1"
        assert result.filters.get("namespace") == "qube"
        assert result.raw_query == query

    def test_script_search_query(self):
        """Test parsing a script search query."""
        query = "script lineage fork"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.LINEAGE_TRACE
        assert result.raw_query == query

    def test_telemetry_check_query(self):
        """Test parsing a telemetry check query."""
        query = "telemetry check qube"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.TELEMETRY_CHECK
        assert result.filters is not None
        assert result.filters.get("namespace") == "qube"

    def test_relay_status_query(self):
        """Test parsing a relay status query."""
        query = "relay status v1"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.RELAY_STATUS
        assert result.filters is not None
        assert result.filters.get("version") == "v1"

    def test_gaming_refs_detection(self):
        """Test detection of gaming culture references."""
        query = "What is a Query to Qbert in T-Rex it Ralph's Sugar rush?"
        result = self.parser.parse(query)
        
        assert result.metadata is not None
        gaming_refs = result.metadata.get("gaming_ref", [])
        assert "Q*bert" in gaming_refs
        assert "Chrome T-Rex Runner" in gaming_refs
        assert "Wreck-It Ralph" in gaming_refs

    def test_unknown_query_type(self):
        """Test handling of unknown query types."""
        query = "some random text without keywords"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.UNKNOWN
        assert result.raw_query == query

    def test_format_response(self):
        """Test formatting of parsed query into response."""
        query = "capsule qube v1"
        parsed = self.parser.parse(query)
        response = self.parser.format_response(parsed)
        
        assert isinstance(response, dict)
        assert "query_type" in response
        assert "target" in response
        assert "filters" in response
        assert "metadata" in response
        assert "raw_query" in response
        assert response["query_type"] == QueryType.CAPSULE_LOOKUP.value

    def test_lineage_trace_query(self):
        """Test parsing lineage/fork queries."""
        query = "find fork lineage for qube"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.LINEAGE_TRACE
        assert result.filters is not None
        assert result.filters.get("namespace") == "qube"

    def test_artifact_find_query(self):
        """Test parsing artifact find queries."""
        query = "artifact relay qube cinematic"
        result = self.parser.parse(query)
        
        assert result.query_type == QueryType.ARTIFACT_FIND
        assert result.filters is not None
        assert result.filters.get("namespace") == "qube"

    def test_issue_43_query(self):
        """Test the actual query from Issue #43."""
        query = "What is a Query to Qbert in T-Rex it Ralph's Sugar Hi coke race in Esco's Bars? 2 Jay Zed's? Or 1MC? Need NOS? Street Fighter Mechanical SW Joys of Stix in the Middle of Emulated Numberland?"
        result = self.parser.parse(query)
        
        # Should detect gaming references
        gaming_refs = result.metadata.get("gaming_ref", [])
        assert len(gaming_refs) > 0
        assert any("bert" in ref.lower() for ref in gaming_refs)
        assert any("rex" in ref.lower() for ref in gaming_refs)
        
        # Should have raw query preserved
        assert result.raw_query == query
