"""Three.js scene management and world rendering."""

import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class Vector3:
    """3D vector for Three.js."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class ThreeJSObject:
    """Base object for Three.js scene."""
    id: str
    name: str
    position: Vector3
    rotation: Vector3
    scale: Vector3
    visible: bool = True
    user_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.user_data is None:
            self.user_data = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position.to_dict(),
            "rotation": self.rotation.to_dict(),
            "scale": self.scale.to_dict(),
            "visible": self.visible,
            "userData": self.user_data,
        }


class SceneManager:
    """Manages Three.js scene graph and rendering state."""

    def __init__(self, scene_id: str = "A2A_World"):
        self.scene_id = scene_id
        self.objects: Dict[str, ThreeJSObject] = {}
        self.lights: Dict[str, Dict[str, Any]] = {}
        self.cameras: Dict[str, Dict[str, Any]] = {}
        self.active_camera = "main_camera"
        self._init_default_lights()
        self._init_default_camera()

    def _init_default_lights(self) -> None:
        """Initialize default lighting."""
        # Ambient light
        self.lights["ambient"] = {
            "type": "AmbientLight",
            "color": 0xffffff,
            "intensity": 0.6,
        }

        # Directional light (sun)
        self.lights["directional"] = {
            "type": "DirectionalLight",
            "color": 0xffffff,
            "intensity": 0.8,
            "position": {"x": 100, "y": 100, "z": 100},
            "castShadow": True,
        }

    def _init_default_camera(self) -> None:
        """Initialize default orthographic camera."""
        self.cameras["main_camera"] = {
            "type": "OrthographicCamera",
            "position": {"x": 0, "y": 150, "z": 150},
            "lookAt": {"x": 0, "y": 0, "z": 0},
            "zoom": 1.0,
            "far": 5000,
        }

    def add_object(self, obj: ThreeJSObject) -> None:
        """Add object to scene."""
        self.objects[obj.id] = obj

    def get_object(self, obj_id: str) -> Optional[ThreeJSObject]:
        """Get object by ID."""
        return self.objects.get(obj_id)

    def remove_object(self, obj_id: str) -> bool:
        """Remove object from scene."""
        if obj_id in self.objects:
            del self.objects[obj_id]
            return True
        return False

    def update_object_position(self, obj_id: str, position: Vector3) -> bool:
        """Update object position."""
        obj = self.get_object(obj_id)
        if obj:
            obj.position = position
            return True
        return False

    def update_object_rotation(self, obj_id: str, rotation: Vector3) -> bool:
        """Update object rotation."""
        obj = self.get_object(obj_id)
        if obj:
            obj.rotation = rotation
            return True
        return False

    def set_object_visibility(self, obj_id: str, visible: bool) -> bool:
        """Set object visibility."""
        obj = self.get_object(obj_id)
        if obj:
            obj.visible = visible
            return True
        return False

    def export_scene_json(self) -> str:
        """Export scene as JSON for Three.js."""
        serialized_objects = [obj.to_dict() for obj in self.objects.values()]
        scene_data = {
            "metadata": {
                "type": "Object",
                "version": 4.5,
                "generator": "A2A_SceneManager",
            },
            "object": {
                "uuid": self.scene_id,
                "type": "Scene",
                "name": self.scene_id,
                "children": serialized_objects,
                "background": 0x87ceeb,  # Sky blue
            },
            # Compatibility key for consumers that expect a flat "objects" list.
            "objects": serialized_objects,
            "lights": self.lights,
            "cameras": self.cameras,
        }
        return json.dumps(scene_data, indent=2)

    def get_scene_dict(self) -> Dict[str, Any]:
        """Get scene as dictionary."""
        return {
            "scene_id": self.scene_id,
            "object_count": len(self.objects),
            "objects": [obj.to_dict() for obj in self.objects.values()],
            "lights": self.lights,
            "cameras": self.cameras,
            "active_camera": self.active_camera,
        }

    def __repr__(self) -> str:
        return (
            f"<SceneManager scene={self.scene_id} "
            f"objects={len(self.objects)} lights={len(self.lights)}>"
        )
