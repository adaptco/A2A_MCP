#include "engine/Physics.hpp"
#include <algorithm>
#include <cmath>

namespace engine {

void Physics::ApplyGravity(Vector2 &velocity, float gravity) {
  velocity.y += gravity;
}

void Physics::UpdatePosition(Vector2 &position, const Vector2 &velocity,
                             float dt) {
  position.x += velocity.x * dt;
  position.y += velocity.y * dt;
}

bool Physics::CheckCollision(const AABB &a, const AABB &b) {
  return (a.min.x < b.max.x && a.max.x > b.min.x && a.min.y < b.max.y &&
          a.max.y > b.min.y);
}

void Physics::EnforceBounds(Vector2 &position, const AABB &bounds) {
  position.x = std::max(bounds.min.x, std::min(position.x, bounds.max.x));
  position.y = std::max(bounds.min.y, std::min(position.y, bounds.max.y));
}

Vector2 Physics::ResolveCollision(const AABB &agentBox, const AABB &tileBox,
                                  Vector2 &velocity) {
  float overlapX = std::min(agentBox.max.x, tileBox.max.x) -
                   std::max(agentBox.min.x, tileBox.min.x);
  float overlapY = std::min(agentBox.max.y, tileBox.max.y) -
                   std::max(agentBox.min.y, tileBox.min.y);

  Vector2 correction = {0, 0};

  if (overlapX < overlapY) {
    if (agentBox.min.x < tileBox.min.x) {
      correction.x = -overlapX;
      if (velocity.x > 0)
        velocity.x = 0;
    } else {
      correction.x = overlapX;
      if (velocity.x < 0)
        velocity.x = 0;
    }
  } else {
    if (agentBox.min.y < tileBox.min.y) {
      correction.y = -overlapY;
      if (velocity.y > 0)
        velocity.y = 0;
    } else {
      correction.y = overlapY;
      if (velocity.y < 0)
        velocity.y = 0;
    }
  }
  return correction;
}

} // namespace engine
