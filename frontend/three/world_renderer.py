"""Base44 world renderer for Three.js."""

from typing import Dict, Any, List, Optional
from frontend.three.scene_manager import SceneManager, ThreeJSObject, Vector3
from specs.loader import get_loader


class ZoneRenderer:
    """Renders a single Base44 zone."""

    CELL_SIZE = 100  # Meters per cell in world space
    LAYER_HEIGHT = 50  # Vertical separation between layers

    def __init__(self, zone_id: str, zone_data: Dict[str, Any]):
        self.zone_id = zone_id
        self.zone_data = zone_data
        self.poly_id = f"zone_{zone_id}"

    def get_zone_bounds(self) -> Dict[str, float]:
        """Calculate world-space bounds for this zone."""
        grid_pos = self.zone_data.get("grid_pos", [0, 0])
        layer = self.zone_data.get("layer", 0)

        x_min = grid_pos[0] * self.CELL_SIZE
        x_max = x_min + self.CELL_SIZE
        z_min = grid_pos[1] * self.CELL_SIZE
        z_max = z_min + self.CELL_SIZE
        y = layer * self.LAYER_HEIGHT

        return {
            "x_min": x_min,
            "x_max": x_max,
            "z_min": z_min,
            "z_max": z_max,
            "y": y,
        }

    def create_mesh(self) -> ThreeJSObject:
        """Create Three.js mesh for zone."""
        bounds = self.get_zone_bounds()
        center_x = (bounds["x_min"] + bounds["x_max"]) / 2
        center_z = (bounds["z_min"] + bounds["z_max"]) / 2
        position = Vector3(x=center_x, y=bounds["y"], z=center_z)

        difficulty = self.zone_data.get("difficulty_rating", 1)
        color_intensity = 0.3 + (difficulty / 4) * 0.7

        obj = ThreeJSObject(
            id=self.poly_id,
            name=self.zone_data.get("name", f"Zone {self.zone_id}"),
            position=position,
            rotation=Vector3(),
            scale=Vector3(x=self.CELL_SIZE, y=5, z=self.CELL_SIZE),
            user_data={
                "zone_id": self.zone_id,
                "layer": self.zone_data.get("layer"),
                "difficulty": difficulty,
                "speed_limit": self.zone_data.get("zone_speed_limit_mph"),
                "obstacles": self.zone_data.get("obstacle_density"),
                "color": int(0xffffff * color_intensity),
            },
        )
        return obj


class WorldRenderer:
    """Renders complete Base44 world with all zones."""

    def __init__(self):
        self.scene = SceneManager(scene_id="Base44_World")
        self.zone_renderers: Dict[str, ZoneRenderer] = {}
        self.loader = get_loader()
        self._render_world()

    def _render_world(self) -> None:
        """Load Base44 map and render all zones."""
        base44_data = self.loader.load_base44_map()
        zones = base44_data.get("zones", {})

        for zone_id, zone_data in zones.items():
            renderer = ZoneRenderer(zone_id, zone_data)
            self.zone_renderers[zone_id] = renderer

            # Create and add mesh
            mesh = renderer.create_mesh()
            self.scene.add_object(mesh)

    def get_zone_at_position(
        self, x: float, z: float, layer: int
    ) -> Optional[str]:
        """Find zone containing position."""
        cell_size = ZoneRenderer.CELL_SIZE

        for zone_id, renderer in self.zone_renderers.items():
            if renderer.zone_data.get("layer") != layer:
                continue

            bounds = renderer.get_zone_bounds()
            if (
                bounds["x_min"] <= x <= bounds["x_max"]
                and bounds["z_min"] <= z <= bounds["z_max"]
            ):
                return zone_id

        return None

    def get_speed_limit_at_position(self, x: float, z: float, layer: int) -> int:
        """Get speed limit for position."""
        zone_id = self.get_zone_at_position(x, z, layer)
        if zone_id and zone_id in self.zone_renderers:
            zone_data = self.zone_renderers[zone_id].zone_data
            return zone_data.get("zone_speed_limit_mph", 55)
        return 55  # Default

    def export_scene(self) -> str:
        """Export scene as JSON."""
        return self.scene.export_scene_json()

    def get_scene_dict(self) -> Dict[str, Any]:
        """Get scene as dictionary."""
        return self.scene.get_scene_dict()

    def __repr__(self) -> str:
        return (
            f"<WorldRenderer zones={len(self.zone_renderers)} "
            f"objects={len(self.scene.objects)}>"
        )
