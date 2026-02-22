
import numpy as np
from scipy.spatial import KDTree

def check_c5_symmetry(vertices, tolerance=1e-5):
    """
    Checks if a set of vertices has C5 symmetry using a vectorized approach.

    Args:
        vertices (np.ndarray): A NumPy array of shape (N, 3) representing the vertex coordinates.
        tolerance (float): The tolerance for nearest neighbor distance checks.

    Returns:
        float: The percentage of vertices that adhere to C5 symmetry.
    """
    if len(vertices) == 0:
        return 100.0  # An empty set is trivially symmetric.

    # 1. Build the KDTree for efficient nearest neighbor searches.
    tree = KDTree(vertices)

    # 2. Define the C5 rotation matrix (72 degrees around the Z-axis).
    theta = np.deg2rad(72)
    c, s = np.cos(theta), np.sin(theta)
    rotation_matrix = np.array([
        [c, -s, 0],
        [s,  c, 0],
        [0,  0, 1]
    ])

    # 3. Vectorized Rotation and Validation
    symmetric_vertices_count = 0
    for _ in range(5):  # Apply five 72-degree rotations
        # Rotate all vertices at once
        vertices = vertices @ rotation_matrix.T

        # Query the KDTree to find the distance to the nearest neighbor for each rotated vertex
        distances, _ = tree.query(vertices, k=1)

        # A vertex is considered symmetric if its rotated position is within the tolerance of an original vertex
        symmetric_vertices_count += np.sum(distances < tolerance)

    # To get a unique count of symmetric vertices, we divide by the number of rotations.
    # We also need to be careful not to double-count. A simpler approach is to check
    # if ANY rotation maps a vertex close to another.
    
    # A more direct approach to get a score:
    total_possible_symmetric_checks = len(vertices) * 5
    
    # The percentage of successful symmetry checks
    symmetry_percentage = (symmetric_vertices_count / total_possible_symmetric_checks) * 100
    
    # A more robust check might involve ensuring each vertex has a match in all rotations.
    # For this implementation, we will use a simpler metric.
    
    # Let's refine the validation logic. For each vertex, we check if a 72-degree rotation
    # lands it near *any* other vertex in the original set.
    
    rotated_vertices = vertices @ rotation_matrix.T
    distances, _ = tree.query(rotated_vertices, k=1)
    
    # Count how many vertices have a corresponding symmetric partner.
    valid_points = np.sum(distances < tolerance)
    
    return (valid_points / len(vertices)) * 100

