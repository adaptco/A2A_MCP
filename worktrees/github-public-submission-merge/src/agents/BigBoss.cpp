#include "agents/BigBoss.hpp"
#include "engine/WorldModel.hpp"
#include <cmath>
#include <iostream>

namespace agents {

BigBoss::BigBoss(engine::Vector2 startPos) : Boss(startPos), rageTimer_(0.0f) {
  health_ = 500; // Big Boss has more health
}

void BigBoss::Update(float dt, const engine::Vector2 &target) {
  rageTimer_ += dt;
  float speed = 0.5f; // Slower than normal boss

  if (rageTimer_ > 5.0f) {
    // Rage mode! Move faster
    speed = 2.0f;
    if (rageTimer_ > 8.0f) {
      rageTimer_ = 0.0f; // Reset rage
    }
  }

  // Simple tracking
  float dir = (target.x - position_.x);
  if (std::abs(dir) > 1.0f) {
    position_.x += (dir > 0 ? 1.0f : -1.0f) * speed * dt;
  }
}

void BigBoss::DeployEmergence(engine::WorldModel *world) {
  std::cout << ">> BIG BOSS: I AM DEPLOYING THE MODEL FOR EMERGENCE! <<"
            << std::endl;
  // Spawn the Genesis Plane at (0, 500) with size 1000x50
  if (world) {
    world->SpawnPlane({0, 500}, 1000, 50);
  }
}

} // namespace agents
