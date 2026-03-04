#include "engine/WorldModel.hpp"
#include <iostream>

namespace engine {

WorldModel::WorldModel() {}

void WorldModel::LoadLevel(int levelId) {
  currentLevel_ = levelId;
  tiles_.clear();
  std::cout << "Generating Level " << levelId << "..." << std::endl;

  // Procedural Gen / Mocking
  // Floor
  tiles_.push_back({TileType::Platform, {{-100, 10}, {1000, 20}}});

  // Boss Room Wall
  tiles_.push_back({TileType::Platform, {{500, -100}, {520, 10}}});

  // Level Specifics
  if (levelId == 0) {
    // HOME WORLD / HUB: Stable, symmetric training environment
    // Y-down coordinates: floor at Y=20
    tiles_.push_back({TileType::Platform, {{-400, 20}, {400, 25}}});
    tiles_.push_back({TileType::Platform, {{-200, 15}, {-100, 16}}});
    tiles_.push_back({TileType::Platform, {{100, 15}, {200, 16}}});
    spawnPoint_ = {0, 10};
  } else if (levelId == 1) {
    // Wily Castle logic
    // Floor
    tiles_.push_back({TileType::Platform, {{-100, 50}, {500, 60}}});
    // Spikes
    tiles_.push_back({TileType::Spikes, {{100, 48}, {200, 50}}});
    // Boss Gate
    tiles_.push_back({TileType::BossGate, {{400, 40}, {410, 50}}});
    spawnPoint_ = {-50, 40};
  }

  // BUG FIX: Do not reset spawnPoint_ here!
}

bool WorldModel::IsSolid(const Vector2 &pos) const {
  // Simple point check against AABBs
  for (const auto &tile : tiles_) {
    // Platform, Spikes, and BossGate are considered solid for this simple check
    if (tile.type == TileType::Platform || tile.type == TileType::Spikes || tile.type == TileType::BossGate) {
      if (pos.x >= tile.bounds.min.x && pos.x <= tile.bounds.max.x &&
          pos.y >= tile.bounds.min.y && pos.y <= tile.bounds.max.y) {
        return true;
      }
    }
  }
  return false;
}

const std::vector<Tile> &WorldModel::GetTiles() const { return tiles_; }

Vector2 WorldModel::GetSpawnPoint() const { return spawnPoint_; }

int WorldModel::GetCurrentLevel() const { return currentLevel_; }

void WorldModel::SpawnPlane(Vector2 origin, float width, float height) {
  std::cout << ">> GENESIS EVENT: Spawning Plane at " << origin.x << ","
            << origin.y << " <<" << std::endl;
  // Create a new platform tile at the origin
  // Note: Y is usually up or down depending on coord sys. Assuming Y-down
  // (screen coords) or Y-up? Physics usually Y-up, but Canvas is Y-down.
  // LevelGen used {{-100, 10}, {1000, 20}} implying Y=10 to 20 is a floor.

  Tile t;
  t.type = TileType::Platform;
  t.bounds.min = origin;
  t.bounds.max = {origin.x + width, origin.y + height};
  tiles_.push_back(t);
}

} // namespace engine
