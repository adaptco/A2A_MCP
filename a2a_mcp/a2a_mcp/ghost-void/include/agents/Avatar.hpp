#pragma once

#include "engine/Physics.hpp"
#include "engine/WorldModel.hpp"

namespace agents {

enum class AvatarState { Idle, Running, Jumping, Falling, Shooting };

class Avatar {
public:
  Avatar(engine::Vector2 startPos);
  void Update(float dt, const engine::WorldModel &world);
  void Jump();
  void Move(float dir);
  void Shoot();

  engine::Vector2 GetPosition() const;
  AvatarState GetState() const;

private:
  engine::Vector2 position_;
  engine::Vector2 velocity_;
  AvatarState state_;
  bool isGrounded_;
};

} // namespace agents
