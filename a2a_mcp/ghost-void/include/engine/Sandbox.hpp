#pragma once

#include "WorldModel.hpp"
#include "SpriteRenderer.hpp"
#include "CitySimulation.hpp"
#include "MonsterBattle.hpp"
#include <memory>

namespace agents {
class Avatar;
class Boss;
} // namespace agents

namespace engine {

class Sandbox {
public:
  Sandbox();
  virtual ~Sandbox();
  void Initialize();
  void LoadLevel(int levelId);
  void SpawnPlane(Vector2 origin, float width, float height);
  void TriggerGenesis();
  void Update(float dt);
  const WorldModel &GetWorld() const;

private:
  std::unique_ptr<WorldModel> world_;
  std::unique_ptr<agents::Avatar> avatar_;
  std::unique_ptr<agents::Boss> boss_;
  std::unique_ptr<SpriteRenderer> renderer_;
  std::unique_ptr<CitySimulation> city_;
  std::unique_ptr<BattleSystem> battle_;
};

} // namespace engine
