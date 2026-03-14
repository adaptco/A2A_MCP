#pragma once

#include "engine/Physics.hpp"

namespace engine {
class WorldModel;
}

namespace agents {

class Boss {
public:
  virtual ~Boss() = default;
  Boss(engine::Vector2 startPos);
  virtual void Update(float dt, const engine::Vector2 &target);
  virtual void DeployEmergence(engine::WorldModel *world) {}

  engine::Vector2 GetPosition() const;

protected:
  engine::Vector2 position_;
  int health_;
};

} // namespace agents
