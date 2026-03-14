import hashlib
import pytest
from ssot.binder import MerkleTree

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def test_merkle_tree_empty():
    """Test that an empty tree returns an empty string root."""
    tree = MerkleTree(leaves=[])
    assert tree.root() == ""

def test_merkle_tree_single_leaf():
    """Test that a tree with a single leaf returns the leaf itself as root."""
    leaf = sha256("leaf1")
    tree = MerkleTree(leaves=[leaf])
    assert tree.root() == leaf

def test_merkle_tree_two_leaves():
    """Test a tree with two leaves (simple pair)."""
    leaf1 = sha256("leaf1")
    leaf2 = sha256("leaf2")

    # Expected: hash(leaf1 + leaf2)
    expected = sha256(leaf1 + leaf2)

    tree = MerkleTree(leaves=[leaf1, leaf2])
    assert tree.root() == expected

def test_merkle_tree_three_leaves():
    """Test a tree with three leaves (odd number handling).

    The implementation duplicates the last leaf if the count is odd.
    Level 0: [L1, L2, L3] -> [L1, L2, L3, L3]
    Level 1: [hash(L1+L2), hash(L3+L3)]
    Level 2: [hash(H1 + H2)]
    """
    leaf1 = sha256("leaf1")
    leaf2 = sha256("leaf2")
    leaf3 = sha256("leaf3")

    h1 = sha256(leaf1 + leaf2)
    h2 = sha256(leaf3 + leaf3)
    expected = sha256(h1 + h2)

    tree = MerkleTree(leaves=[leaf1, leaf2, leaf3])
    assert tree.root() == expected

def test_merkle_tree_deterministic():
    """Test that the same leaves always produce the same root."""
    leaves = [sha256(str(i)) for i in range(5)]
    tree1 = MerkleTree(leaves)
    tree2 = MerkleTree(leaves)
    assert tree1.root() == tree2.root()

def test_merkle_tree_four_leaves():
    """Test a balanced tree with 4 leaves."""
    leaves = [sha256(str(i)) for i in range(4)]
    # L1, L2, L3, L4
    # H1 = hash(L1+L2), H2 = hash(L3+L4)
    # Root = hash(H1+H2)

    h1 = sha256(leaves[0] + leaves[1])
    h2 = sha256(leaves[2] + leaves[3])
    expected = sha256(h1 + h2)

    tree = MerkleTree(leaves)
    assert tree.root() == expected
