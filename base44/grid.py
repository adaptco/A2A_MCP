"""Base44 grid primitives for world navigation."""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, List, Any
from enum import Enum


class ZoneLayer(int, Enum):
    """Logical altitude/theme layers in Base44 space."""
    GROUND = 0
    ELEVATED = 1
    AERIAL = 2


@dataclass
class WorldBounds:
    """3D bounding box for a grid cell."""
    x_min: float = 0.0
    x_max: float = 100.0
    y_min: float = 0.0
    y_max: float = 100.0
    z_min: float = 0.0
    z_max: float = 100.0

    def contains(self, point: Tuple[float, float, float]) -> bool:
        """Check if point is within bounds."""
        x, y, z = point
        return (self.x_min <= x <= self.x_max and
                self.y_min <= y <= self.y_max and
                self.z_min <= z <= self.z_max)


@dataclass
class GridCell:
    """Single cell in Base44 grid."""
    cell_id: int  # 0-43
    grid_x: int   # 0-3 (4x4 macro grid)
    grid_y: int   # 0-3
    layer: ZoneLayer = ZoneLayer.GROUND
    world_bounds: WorldBounds = field(default_factory=WorldBounds)
    spawn_points: List[Tuple[float, float, float]] = field(default_factory=list)
    wasd_blocking_map: Dict[str, bool] = field(default_factory=lambda: {
        "N": False, "S": False, "E": False, "W": False
    })  # Can move North, South, East, West
    properties: Dict[str, Any] = field(default_factory=dict)

    def is_passable(self, direction: str) -> bool:
        """Check if a WASD direction is passable from this cell."""
        return not self.wasd_blocking_map.get(direction, True)

    def __repr__(self) -> str:
        return f"<GridCell id={self.cell_id} pos=({self.grid_x},{self.grid_y}) layer={self.layer.name}>"


@dataclass
class ZoneChangeEvent:
    """Event fired when entity crosses cell boundaries."""
    from_cell_id: int
    to_cell_id: int
    from_pos: Tuple[float, float, float]
    to_pos: Tuple[float, float, float]
    direction: str  # "N", "S", "E", "W", or diagonal


class Base44Grid:
    """
    4x4 macro grid × 3 layers = 48 logical zones.
    Reserve 4 for system use → Base44 logical space (0-43).
    """

    MACRO_WIDTH = 4     # 4x4 grid
    MACRO_HEIGHT = 4
    NUM_LAYERS = 3      # ground, elevated, aerial
    RESERVED_CELLS = 4  # system cells (44-47)
    USABLE_CELLS = 44   # 0-43

    def __init__(self):
        self._cells: Dict[int, GridCell] = {}
        self._generate_default_grid()

    def _generate_default_grid(self) -> None:
        """Initialize default 4x4x3 grid with basic cell data."""
        cell_id = 0
        for layer in range(self.NUM_LAYERS):
            for y in range(self.MACRO_HEIGHT):
                for x in range(self.MACRO_WIDTH):
                    if cell_id >= self.USABLE_CELLS:
                        break

                    # Compute bounding box for this cell
                    bounds = WorldBounds(
                        x_min=float(x * 100),
                        x_max=float((x + 1) * 100),
                        y_min=float(y * 100),
                        y_max=float((y + 1) * 100),
                        z_min=float(layer * 100),
                        z_max=float((layer + 1) * 100)
                    )

                    cell = GridCell(
                        cell_id=cell_id,
                        grid_x=x,
                        grid_y=y,
                        layer=ZoneLayer(layer),
                        world_bounds=bounds,
                        spawn_points=[(50.0 + x * 100, 50.0 + y * 100, 50.0 + layer * 100)]
                    )
                    self._cells[cell_id] = cell
                    cell_id += 1

    def get_cell(self, cell_id: int) -> Optional[GridCell]:
        """Retrieve a cell by ID."""
        return self._cells.get(cell_id)

    def get_cell_at_position(self, pos: Tuple[float, float, float]) -> Optional[GridCell]:
        """Find cell containing a world position."""
        for cell in self._cells.values():
            if cell.world_bounds.contains(pos):
                return cell
        return None

    def get_neighbors(self, cell_id: int) -> Dict[str, Optional[int]]:
        """Get adjacent cell IDs (N, S, E, W)."""
        cell = self.get_cell(cell_id)
        if not cell:
            return {}

        neighbors = {}
        # Compute neighbor coords (wrapping not implemented; None if edge)
        for direction, (dx, dy) in [
            ("N", (0, -1)), ("S", (0, 1)),
            ("E", (1, 0)), ("W", (-1, 0))
        ]:
            nx, ny = cell.grid_x + dx, cell.grid_y + dy
            if 0 <= nx < self.MACRO_WIDTH and 0 <= ny < self.MACRO_HEIGHT:
                neighbor_id = cell.layer.value * (self.MACRO_WIDTH * self.MACRO_HEIGHT) + ny * self.MACRO_WIDTH + nx
                neighbors[direction] = neighbor_id
            else:
                neighbors[direction] = None

        return neighbors

    def list_cells(self) -> List[GridCell]:
        """Return all cells."""
        return sorted(self._cells.values(), key=lambda c: c.cell_id)

    def __repr__(self) -> str:
        return f"<Base44Grid cells={len(self._cells)} layers={self.NUM_LAYERS}>"
