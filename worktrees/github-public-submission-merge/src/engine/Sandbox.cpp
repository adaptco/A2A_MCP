#include "engine/Sandbox.hpp"
#include "agents/Avatar.hpp"
#include "agents/Boss.hpp"
#include "engine/CitySimulation.hpp"
#include <iostream>

namespace engine {

Sandbox::Sandbox()
    : world_(std::make_unique<WorldModel>()),
      renderer_(std::make_unique<SpriteRenderer>()),
      city_(std::make_unique<CitySimulation>(16, 16)),
      battle_(std::make_unique<BattleSystem>()) {

    // Initialize some zones for demo
    city_->SetZone(5, 5, ZoneType::PowerPlant);
    city_->SetZone(6, 5, ZoneType::Residential);
    city_->SetZone(4, 5, ZoneType::Residential);
    city_->SetZone(5, 4, ZoneType::Residential);
    city_->SetZone(5, 6, ZoneType::Residential);
}

Sandbox::~Sandbox() = default;

void Sandbox::Initialize() {
  std::cout << "Initializing Sandbox..." << std::endl;
}

void Sandbox::LoadLevel(int levelId) {
  std::cout << "Loading level " << levelId << "..." << std::endl;
}

void Sandbox::SpawnPlane(Vector2 origin, float width, float height) {
  std::cout << "Spawning plane at (" << origin.x << ", " << origin.y << ") with size " << width << "x" << height << "..." << std::endl;
}

void Sandbox::TriggerGenesis() {
  std::cout << "Triggering Genesis..." << std::endl;
}

void Sandbox::Update(float dt) {
  // Update city simulation
  city_->Update(dt);
}

const WorldModel &Sandbox::GetWorld() const {
  return *world_;
}

} // namespace engine
