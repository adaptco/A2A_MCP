import pytest
from orchestrator.dmn_parser import DMNParser

@pytest.fixture
def parser():
    return DMNParser()

def test_valid_dmn_parse(parser):
    valid_data = {
        "nodes": [
            {"id": "n1", "type": "Structural"},
            {"id": "n2", "type": "Behavioral"}
        ],
        "edges": [
            {"source": "n1", "target": "n2"}
        ]
    }

    ast, report, receipt = parser.parse(valid_data)

    assert report.valid
    assert receipt.verdict == "ACCEPTED"
    assert ast["graph"]["nodes"][0]["id"] == "n1"

def test_invalid_geometry_bad_type(parser):
    invalid_data = {
        "nodes": [
            {"id": "n1", "type": "UnknownType"}
        ],
        "edges": []
    }

    ast, report, receipt = parser.parse(invalid_data)

    assert not report.valid
    assert "Invalid node type: UnknownType" in report.reasons
    assert receipt.verdict == "REJECTED_GEOMETRY"
    assert ast is None

def test_invalid_constitution_self_ref(parser):
    invalid_data = {
        "nodes": [
            {"id": "n1", "type": "Structural"}
        ],
        "edges": [
            {"source": "n1", "target": "n1"}
        ]
    }

    ast, report, receipt = parser.parse(invalid_data)

    assert not report.valid
    assert "Self-referential edge detected: n1" in report.reasons
    assert receipt.verdict == "REJECTED_CONSTITUTION"
    assert ast is None

def test_determinism(parser):
    data = {
        "nodes": [
            {"id": "b", "type": "Structural"},
            {"id": "a", "type": "Structural"}
        ],
        "edges": []
    }

    ast1, _, receipt1 = parser.parse(data)
    ast2, _, receipt2 = parser.parse(data)

    assert receipt1.hash == receipt2.hash
    # Check if AST nodes are sorted by ID as per implementation
    assert ast1["graph"]["nodes"][0]["id"] == "a"
    assert ast1["graph"]["nodes"][1]["id"] == "b"
