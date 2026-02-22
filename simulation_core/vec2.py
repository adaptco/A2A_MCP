from dataclasses import dataclass
import math

@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def clamp(self, max_len: float) -> "Vec2":
        length = self.length()
        if length <= max_len or length == 0.0:
            return self
        scale = max_len / length
        return Vec2(self.x * scale, self.y * scale)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}
