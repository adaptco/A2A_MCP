#include "../../include/agents/Boss.hpp"
#include <cmath>

namespace agents {

Boss::Boss(engine::Vector2 startPos) : position_(startPos), health_(100) {}

void Boss::Update(float dt, const engine::Vector2 &target) {
  // Simple AI: Move towards target (Avatar)
  float dir = (target.x - position_.x);
  if (std::abs(dir) > 1.0f) {
    position_.x += (dir > 0 ? 1.0f : -1.0f) * dt;
  }
}

engine::Vector2 Boss::GetPosition() const { return position_; }

} // namespace agents
