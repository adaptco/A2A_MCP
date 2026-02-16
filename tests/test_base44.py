
import pytest
from base44.grid import Base44Grid, GridCell, ZoneLayer, WorldBounds

def test_grid_initialization():
    """Verify grid is created with correct dimensions and cell count."""
    grid = Base44Grid()
    cells = grid.list_cells()
    
    # Validation:
    # 4x4 macro grid * 3 layers = 48 cells total
    # But code has: RESERVED_CELLS = 4, USABLE_CELLS = 44
    # The loop breaks at USABLE_CELLS
    assert len(cells) == 44
    
    # Check bounds of first cell (0,0,0)
    c0 = grid.get_cell(0)
    assert c0 is not None
    assert c0.grid_x == 0
    assert c0.grid_y == 0
    assert c0.layer == ZoneLayer.GROUND
    assert c0.world_bounds == WorldBounds(0.0, 100.0, 0.0, 100.0, 0.0, 100.0)

def test_coordinate_system():
    """Verify WorldBounds logic."""
    bounds = WorldBounds(0.0, 100.0, 0.0, 100.0, 0.0, 100.0)
    
    # Inside
    assert bounds.contains((50.0, 50.0, 50.0))
    # Edges (inclusive)
    assert bounds.contains((0.0, 0.0, 0.0))
    assert bounds.contains((100.0, 100.0, 100.0))
    # Outside
    assert not bounds.contains((-1.0, 50.0, 50.0))
    assert not bounds.contains((101.0, 50.0, 50.0))

def test_get_cell_at_position():
    """Verify spatial lookup."""
    grid = Base44Grid()
    
    # Test ground layer cell 0 (0-100, 0-100, 0-100)
    c1 = grid.get_cell_at_position((50.0, 50.0, 50.0))
    assert c1 is not None
    assert c1.cell_id == 0
    
    # Test cell 5 (x=1, y=1 => 100-200, 100-200)
    # Cell calculation in grid.py:
    # id = layer * 16 + y * 4 + x
    # id 5 = 0*16 + 1*4 + 1 -> x=1, y=1, layer=0
    # Bounds: x=100-200, y=100-200, z=0-100
    c5 = grid.get_cell_at_position((150.0, 150.0, 50.0))
    assert c5 is not None
    assert c5.cell_id == 5

def test_neighbors_ground_center():
    """Verify neighbors for a central cell (has N, S, E, W)."""
    grid = Base44Grid()
    # Cell 5 is at (1,1) in Ground layer (0). 
    # Neighbors:
    # N: (1,0) -> id 1
    # S: (1,2) -> id 9
    # E: (2,1) -> id 6
    # W: (0,1) -> id 4
    
    neighbors = grid.get_neighbors(5)
    assert neighbors["N"] == 1
    assert neighbors["S"] == 9
    assert neighbors["E"] == 6
    assert neighbors["W"] == 4

def test_neighbors_ground_corner():
    """Verify neighbors for a corner cell (0,0)."""
    grid = Base44Grid()
    # Cell 0: (0,0) Ground
    # N: (0,-1) -> None
    # S: (0,1) -> id 4
    # E: (1,0) -> id 1
    # W: (-1,0) -> None
    
    neighbors = grid.get_neighbors(0)
    assert neighbors["N"] is None
    assert neighbors["S"] == 4
    assert neighbors["E"] == 1
    assert neighbors["W"] is None

def test_is_passable():
    """Verify passability logic."""
    cell = GridCell(0, 0, 0)
    # Default is all passable (False in blocking map)
    assert cell.is_passable("N")
    assert cell.is_passable("S")
    
    # Block North
    cell.wasd_blocking_map["N"] = True
    assert not cell.is_passable("N")
    assert cell.is_passable("S")
