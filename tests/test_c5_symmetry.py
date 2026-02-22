import numpy as np
import pytest
from a2a_mcp.game_engine import check_c5_symmetry


def create_perfect_pentagon(radius=1.0):
    """Generates vertices for a perfect pentagon on the XY plane."""
    return np.array([
        [radius * np.cos(2 * np.pi * i / 5), radius * np.sin(2 * np.pi * i / 5), 0]
        for i in range(5)
    ])

def test_c5_symmetry_on_perfect_pentagon():
    """Ensures a perfect pentagon yields a 100% symmetry score."""
    pentagon_vertices = create_perfect_pentagon()
    assert check_c5_symmetry(pentagon_vertices) == 100.0

def test_c5_symmetry_with_noise():
    """Verifies that noise vertices are correctly identified."""
    pentagon_vertices = create_perfect_pentagon()
    # Add a vertex that breaks the symmetry
    noise_vertex = np.array([[0.5, 0.5, 0.5]])
    vertices_with_noise = np.vstack([pentagon_vertices, noise_vertex])
    # The score should be less than 100% because of the noise
    assert check_c5_symmetry(vertices_with_noise) < 100.0

def test_empty_dataset():
    """Validates that an empty vertex set doesn't cause a crash."""
    assert check_c5_symmetry(np.array([])) == 100.0

def test_large_dataset_performance_and_precision():
    """Tests precision on a large dataset of 50,000+ vertices."""
    # Create a large cloud of points forming concentric pentagons
    num_rings = 10000
    vertices = np.vstack([create_perfect_pentagon(radius=r) for r in range(1, num_rings + 1)])
    assert vertices.shape[0] == 50000
    assert check_c5_symmetry(vertices, tolerance=1e-5) == 100.0
