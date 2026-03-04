#include "bridge/world_model_c.h"
#include "engine/WorldModel.hpp"

extern "C" {

WorldModelHandle WorldModel_Create() { return new engine::WorldModel(); }

void WorldModel_Destroy(WorldModelHandle handle) {
  if (handle) {
    delete static_cast<engine::WorldModel *>(handle);
  }
}

void WorldModel_LoadLevel(WorldModelHandle handle, int levelId) {
  static_cast<engine::WorldModel *>(handle)->LoadLevel(levelId);
}

int WorldModel_IsSolid(WorldModelHandle handle, CVector2 pos) {
  engine::Vector2 v = {pos.x, pos.y};
  return static_cast<engine::WorldModel *>(handle)->IsSolid(v) ? 1 : 0;
}

int WorldModel_GetTilesCount(WorldModelHandle handle) {
  return static_cast<engine::WorldModel *>(handle)->GetTiles().size();
}

void WorldModel_GetTiles(WorldModelHandle handle, CTile *tiles, int maxCount) {
  auto &wmTiles = static_cast<engine::WorldModel *>(handle)->GetTiles();
  int count = std::min((int)wmTiles.size(), maxCount);

  for (int i = 0; i < count; ++i) {
    tiles[i].type = static_cast<int>(wmTiles[i].type);
    tiles[i].min = {wmTiles[i].bounds.min.x, wmTiles[i].bounds.min.y};
    tiles[i].max = {wmTiles[i].bounds.max.x, wmTiles[i].bounds.max.y};
  }
}

CVector2 WorldModel_GetSpawnPoint(WorldModelHandle handle) {
  engine::Vector2 v =
      static_cast<engine::WorldModel *>(handle)->GetSpawnPoint();
  return {v.x, v.y};
}

int WorldModel_GetCurrentLevel(WorldModelHandle handle) {
  return static_cast<engine::WorldModel *>(handle)->GetCurrentLevel();
}

void WorldModel_SpawnPlane(WorldModelHandle handle, CVector2 origin,
                           float width, float height) {
  engine::Vector2 v = {origin.x, origin.y};
  static_cast<engine::WorldModel *>(handle)->SpawnPlane(v, width, height);
}
}
