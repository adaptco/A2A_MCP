#include "agents/Avatar.hpp"
#include <iostream>

namespace agents {

Avatar::Avatar(engine::Vector2 startPos)
    : position_(startPos), velocity_{0, 0}, state_(AvatarState::Idle),
      isGrounded_(false) {}

void Avatar::Update(float dt, const engine::WorldModel &world) {
  // Apply Gravity
  engine::Physics::ApplyGravity(velocity_);

  // Update Position
  engine::Physics::UpdatePosition(position_, velocity_, dt);

  // Initial simple ground check
  if (position_.y > 0) { // simple floor at y=0 if no tiles
    position_.y = 0;
    velocity_.y = 0;
    isGrounded_ = true;
  }

  // Check world collision
  if (world.IsSolid(position_)) {
    // Simple resolve - this is very basic
    // In real engine, would need previous pos to resolve correctly
    velocity_.x = 0;
    velocity_.y = 0;
  }
}

void Avatar::Jump() {
  if (isGrounded_) {
    velocity_.y = -5.0f; // Jump force
    state_ = AvatarState::Jumping;
    isGrounded_ = false;
    std::cout << "Mega Man Jumps!" << std::endl;
  }
}

void Avatar::Move(float dir) {
  velocity_.x = dir * 2.0f; // Speed
  if (dir != 0)
    state_ = AvatarState::Running;
  else
    state_ = AvatarState::Idle;
}

void Avatar::Shoot() {
  state_ = AvatarState::Shooting;
  std::cout << "pew pew!" << std::endl;
}

engine::Vector2 Avatar::GetPosition() const { return position_; }

AvatarState Avatar::GetState() const { return state_; }

} // namespace agents
