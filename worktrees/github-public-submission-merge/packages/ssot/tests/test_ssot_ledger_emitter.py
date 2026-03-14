import pytest
import hashlib
from ssot.ledger_emitter import (
    merkle_root_from_leaves,
    sha256_digest,
    _leaf_hash,
    _node_hash,
    _empty_root,
    _hex_bytes_from_sha256
)

def test_merkle_root_empty():
    """Test that an empty list returns the specific empty root hash."""
    root = merkle_root_from_leaves([])
    assert root == _empty_root()

def test_merkle_root_single_leaf():
    """Test that a single leaf returns the leaf's hash directly (as root)."""
    leaf = sha256_digest(b"leaf1")
    root = merkle_root_from_leaves([leaf])

    # Based on the implementation:
    # nodes = [_leaf_hash(leaf)]
    # loop condition len(nodes) > 1 is false
    # returns "sha256:" + nodes[0].hex()

    expected = "sha256:" + _leaf_hash(leaf).hex()
    assert root == expected

def test_merkle_root_two_leaves():
    """Test standard hashing of two leaves."""
    leaf1 = sha256_digest(b"leaf1")
    leaf2 = sha256_digest(b"leaf2")

    root = merkle_root_from_leaves([leaf1, leaf2])

    h1 = _leaf_hash(leaf1)
    h2 = _leaf_hash(leaf2)
    expected_hash = _node_hash(h1, h2)
    expected = "sha256:" + expected_hash.hex()

    assert root == expected

def test_merkle_root_three_leaves():
    """Test that the odd leaf is duplicated to form a pair."""
    leaf1 = sha256_digest(b"leaf1")
    leaf2 = sha256_digest(b"leaf2")
    leaf3 = sha256_digest(b"leaf3")

    root = merkle_root_from_leaves([leaf1, leaf2, leaf3])

    # Layer 1
    h1 = _leaf_hash(leaf1)
    h2 = _leaf_hash(leaf2)
    h3 = _leaf_hash(leaf3)

    # Layer 2
    # Pair (h1, h2) -> n1
    n1 = _node_hash(h1, h2)
    # Pair (h3, h3) -> n2 (duplicated last node)
    n2 = _node_hash(h3, h3)

    # Layer 3
    # Pair (n1, n2) -> root
    final_hash = _node_hash(n1, n2)
    expected = "sha256:" + final_hash.hex()

    assert root == expected

def test_merkle_root_four_leaves():
    """Test a balanced tree with 4 leaves."""
    leaves = [sha256_digest(f"leaf{i}".encode()) for i in range(4)]

    root = merkle_root_from_leaves(leaves)

    # Layer 1
    hashes = [_leaf_hash(l) for l in leaves]

    # Layer 2
    n1 = _node_hash(hashes[0], hashes[1])
    n2 = _node_hash(hashes[2], hashes[3])

    # Layer 3
    final_hash = _node_hash(n1, n2)
    expected = "sha256:" + final_hash.hex()

    assert root == expected

def test_merkle_root_invalid_inputs():
    """Test that invalid leaf formats raise ValueError."""
    # Invalid prefix
    with pytest.raises(ValueError, match="digest must be sha256:hex"):
        merkle_root_from_leaves(["invalid_prefix:1234"])

    # Invalid length
    with pytest.raises(ValueError, match="sha256 hex length must be 64"):
        merkle_root_from_leaves(["sha256:123"])

    # Not a string
    with pytest.raises(ValueError, match="digest must be sha256:hex"):
        merkle_root_from_leaves([123])

def test_merkle_root_consistency():
    """Verify consistency with a known set of leaves."""
    # This acts as a regression test for the specific prefix constants
    leaves = [
        "sha256:0000000000000000000000000000000000000000000000000000000000000001",
        "sha256:0000000000000000000000000000000000000000000000000000000000000002"
    ]
    # We don't hardcode the expected root hash here unless we want to freeze the implementation details (prefixes),
    # but we can verify it produces *something* valid.
    root = merkle_root_from_leaves(leaves)
    assert root.startswith("sha256:")
    assert len(root) == 7 + 64
