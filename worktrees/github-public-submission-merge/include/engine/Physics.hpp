#pragma once

#include <vector>

namespace engine {

struct Vector2 {
  float x, y;
};

struct AABB {
  Vector2 min, max;
};

class Physics {
public:
  static void ApplyGravity(Vector2 &velocity, float gravity = 9.8f);
  static void UpdatePosition(Vector2 &position, const Vector2 &velocity,
                             float dt);
  static bool CheckCollision(const AABB &a, const AABB &b);
  static void EnforceBounds(Vector2 &position, const AABB &bounds);
  static Vector2 ResolveCollision(const AABB &agentBox, const AABB &tileBox,
                                  Vector2 &velocity);
};

} // namespace engine
