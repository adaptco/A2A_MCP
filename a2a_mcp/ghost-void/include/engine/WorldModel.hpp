#pragma once

#include "Physics.hpp"

#include <vector>

namespace engine {

enum class TileType { Empty, Platform, Spikes, Ladder, BossGate };

struct Tile {
  TileType type;
  AABB bounds;
};

class WorldModel {
public:
  WorldModel();
  void LoadLevel(int levelId);
  bool IsSolid(const Vector2 &pos) const;
  const std::vector<Tile> &GetTiles() const;
  Vector2 GetSpawnPoint() const;
  int GetCurrentLevel() const;
  void SpawnPlane(Vector2 origin, float width, float height);

private:
  int currentLevel_ = 0;
  std::vector<Tile> tiles_;
  Vector2 spawnPoint_ = {0, 0};
};

} // namespace engine
