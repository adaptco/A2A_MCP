"""Avatar visualization for Three.js UI."""

from typing import Dict, Any, Optional
from avatars.registry import get_avatar_registry
from avatars.avatar import AvatarStyle
from avatars.setup import setup_default_avatars
from frontend.three.scene_manager import ThreeJSObject, Vector3

CANONICAL_AGENTS = [
    "ManagingAgent",
    "OrchestrationAgent",
    "ArchitectureAgent",
    "CoderAgent",
    "TesterAgent",
    "ResearcherAgent",
    "PINNAgent",
]


class AvatarUIPanel:
    """UI panel for displaying avatar information and Judge scores."""

    def __init__(
        self,
        avatar_id: str,
        agent_name: str,
        position: Vector3,
        judge_score: float = 0.5,
    ):
        self.avatar_id = avatar_id
        self.agent_name = agent_name
        self.position = position
        self.judge_score = judge_score
        self.visible = True

    def get_style_colors(self, style: AvatarStyle) -> Dict[str, str]:
        """Get colors based on avatar style."""
        colors = {
            AvatarStyle.ENGINEER: {
                "primary": "#0066cc",
                "secondary": "#003366",
                "accent": "#00ff00",
            },
            AvatarStyle.DESIGNER: {
                "primary": "#ff6600",
                "secondary": "#ff3300",
                "accent": "#ffcc00",
            },
            AvatarStyle.DRIVER: {
                "primary": "#ff0000",
                "secondary": "#dd0000",
                "accent": "#ffff00",
            },
        }
        return colors.get(style, colors[AvatarStyle.ENGINEER])

    def get_score_bar_color(self, score: float) -> str:
        """Get color for Judge score bar."""
        if score >= 0.9:
            return "#00ff00"  # Green - excellent
        elif score >= 0.7:
            return "#ffff00"  # Yellow - good
        elif score >= 0.5:
            return "#ffaa00"  # Orange - acceptable
        else:
            return "#ff0000"  # Red - poor

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary for JSON serialization."""
        return {
            "avatar_id": self.avatar_id,
            "agent_name": self.agent_name,
            "position": self.position.to_dict(),
            "judge_score": self.judge_score,
            "score_bar_color": self.get_score_bar_color(self.judge_score),
            "visible": self.visible,
        }


class AvatarRenderer:
    """Renders agent avatars in the 3D world."""

    def __init__(self):
        self.registry = get_avatar_registry()
        self.avatar_panels: Dict[str, AvatarUIPanel] = {}
        if len(self._canonical_avatars()) < len(CANONICAL_AGENTS):
            setup_default_avatars()
        self._create_avatar_objects()

    def _canonical_avatars(self):
        avatars = []
        for agent_name in CANONICAL_AGENTS:
            avatar = self.registry.get_avatar_for_agent(agent_name)
            if avatar is not None:
                avatars.append(avatar)
        return avatars

    def _create_avatar_objects(self) -> None:
        """Create UI panel for each avatar."""
        avatars = self._canonical_avatars()
        self.avatar_panels = {}

        for idx, avatar in enumerate(avatars):
            # Position avatars in UI space
            x = -200 + (idx % 4) * 100
            y = 300
            z = (idx // 4) * 80

            panel = AvatarUIPanel(
                avatar_id=avatar.profile.avatar_id,
                agent_name=avatar.profile.bound_agent or avatar.profile.name,
                position=Vector3(x=x, y=y, z=z),
                judge_score=0.5,  # Default score
            )

            self.avatar_panels[avatar.profile.avatar_id] = panel

    def update_avatar_score(self, avatar_id: str, score: float) -> bool:
        """Update Judge score for avatar."""
        if avatar_id in self.avatar_panels:
            self.avatar_panels[avatar_id].judge_score = max(0.0, min(1.0, score))
            return True
        return False

    def get_ui_panels_json(self) -> Dict[str, Any]:
        """Export all UI panels as JSON."""
        return {
            "panels": [panel.to_dict() for panel in self.avatar_panels.values()],
            "count": len(self.avatar_panels),
        }

    def create_avatar_representation(
        self, avatar_id: str
    ) -> Optional[ThreeJSObject]:
        """Create 3D representation of avatar (simple sphere)."""
        avatar = self.registry.get_avatar(avatar_id)
        if not avatar:
            return None

        panel = self.avatar_panels.get(avatar_id)
        if not panel:
            return None

        # Get style colors
        style_colors = panel.get_style_colors(avatar.profile.style)

        # Create sphere object
        obj = ThreeJSObject(
            id=f"avatar_{avatar_id}",
            name=avatar.profile.name,
            position=panel.position,
            rotation=Vector3(),
            scale=Vector3(x=10, y=10, z=10),
            user_data={
                "avatar_id": avatar_id,
                "agent_name": avatar.profile.bound_agent,
                "style": avatar.profile.style.value,
                "color": style_colors["primary"],
                "judge_score": panel.judge_score,
            },
        )

        return obj

    def __repr__(self) -> str:
        return f"<AvatarRenderer panels={len(self.avatar_panels)}>"
