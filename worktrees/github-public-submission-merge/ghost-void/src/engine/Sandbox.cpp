#include "engine/Sandbox.hpp"
#include "agents/Avatar.hpp"
#include "agents/BigBoss.hpp"
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

Sandbox::~Sandbox() = default;

void Sandbox::Initialize() {
  std::cout << "Initializing Sandbox..." << std::endl;
  world_->LoadLevel(1); // Default to level 1
  avatar_ = std::make_unique<agents::Avatar>(world_->GetSpawnPoint());
  boss_ = std::make_unique<agents::BigBoss>(Vector2{100, 0});
}

void Sandbox::LoadLevel(int levelId) {
  world_->LoadLevel(levelId);
  if (avatar_) {
    // Reset avatar pos if needed
  }
}

void Sandbox::SpawnPlane(Vector2 origin, float width, float height) {
  // const_cast because GetWorld returns const ref (design flaw in scaffolding
  // fixed here) Actually, friend or just mutable. Let's use const_cast for
  // expediency in this task.
  const_cast<WorldModel &>(*world_).SpawnPlane(origin, width, height);
}

void Sandbox::TriggerGenesis() {
  if (boss_) {
    // Let the boss handle emergence
    boss_->DeployEmergence(world_.get());
  } else {
    // Fallback? Or just log error
    std::cerr << "Cannot deploy emergence: No Boss found!" << std::endl;
  }
}

void Sandbox::Update(float dt) {
  // Simulate Game Loop
  static float time = 0;
  time += dt;

  if (battle_ && battle_->IsActive()) {
      battle_->Update(dt);
      
      // Render Battle Overlay
      // Darken background or draw a battle BG
      renderer_->DrawSprite("battle_bg", {0, 0}, {800, 600}, {{0,0}, {1,1}});
      
      // Draw Monsters
      renderer_->DrawSprite("player_mon", {100, 300}, {64, 64}, {{0,0}, {1,1}});
      renderer_->DrawSprite("enemy_mon", {600, 100}, {64, 64}, {{0,0}, {1,1}});
      
      // Log would be drawn as text/ui elements
      // std::cout << battle_->GetLog() << std::endl; 
      
  } else {
      // Normal Game Loop
      if (city_) {
         city_->Update(dt);
         // Render City Grid (Background layer)
         for(int y=0; y<16; ++y) {
             for(int x=0; x<16; ++x) {
                 const auto& cell = city_->GetCell(x, y);
                 Vector2 pos = { (float)x * 32 + 300, (float)y * 32 };
                 std::string tex = "ground";
                 if(cell.type == ZoneType::Residential) tex = cell.hasPower ? "res_powered" : "res_empty";
                 if(cell.type == ZoneType::PowerPlant) tex = "power_plant";
                 
                 AABB uv = {{0,0}, {32,32}};
                 renderer_->DrawSprite(tex, pos, {32, 32}, uv);
             }
         }
      }

      if (avatar_)
        avatar_->Update(dt, *world_);
      if (boss_ && avatar_)
        boss_->Update(dt, avatar_->GetPosition());

      if (avatar_) {
        // Render Avatar
        // UVs would normally be calculated from sprite sheet based on state/frame
        // For now, mockup UVs
        AABB uv = {{0, 0}, {16, 16}}; 
        renderer_->DrawSprite("megaman_sheet", avatar_->GetPosition(), {16, 16}, uv);

        // Mock Input for demo
        if (time > 1.0f && time < 1.1f)
          avatar_->Jump();
        if (time > 2.0f && time < 2.1f)
          avatar_->Shoot();
          
        // Trigger battle for demo
        if (time > 8.0f && time < 8.1f && battle_) {
            battle_->StartBattle({"Pikachu", MonsterType::Fire, 100, 100, 20}, {"Charizard", MonsterType::Fire, 150, 150, 30});
        }
      }

      if (boss_) {
        // Render Boss
        AABB uv = {{0, 16}, {32, 48}}; 
        renderer_->DrawSprite("boss_sheet", boss_->GetPosition(), {32, 32}, uv);
      }
  }

  // Render Frame
  renderer_->Render();
}

const WorldModel &Sandbox::GetWorld() const { return *world_; }

} // namespace engine
