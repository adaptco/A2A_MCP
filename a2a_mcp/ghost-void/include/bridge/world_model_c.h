#pragma once

#ifdef __cplusplus
extern "C" {
#endif

// Opaque handle for WorldModel
typedef void* WorldModelHandle;

// C-compatible Vector2 struct
typedef struct {
    float x;
    float y;
} CVector2;

// C-compatible Tile struct
typedef struct {
    int type;  // 0=Empty, 1=Platform, 2=Spikes, 3=Ladder, 4=BossGate
    CVector2 min;
    CVector2 max;
} CTile;

// WorldModel C API
WorldModelHandle WorldModel_Create();
void WorldModel_Destroy(WorldModelHandle handle);
void WorldModel_LoadLevel(WorldModelHandle handle, int levelId);
int WorldModel_IsSolid(WorldModelHandle handle, CVector2 pos);
int WorldModel_GetTilesCount(WorldModelHandle handle);
void WorldModel_GetTiles(WorldModelHandle handle, CTile* tiles, int maxCount);
CVector2 WorldModel_GetSpawnPoint(WorldModelHandle handle);
int WorldModel_GetCurrentLevel(WorldModelHandle handle);
void WorldModel_SpawnPlane(WorldModelHandle handle, CVector2 origin, float width, float height);

#ifdef __cplusplus
}
#endif
