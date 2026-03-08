#pragma once

#include <string>
#include <vector>
#include <memory>

namespace engine {

enum class MonsterType { Fire, Water, Grass };

struct Monster {
    std::string name;
    MonsterType type;
    int hp;
    int maxHp;
    int attack;
};

class BattleSystem {
public:
    BattleSystem();
    
    void StartBattle(const Monster& playerMonster, const Monster& enemyMonster);
    void Update(float dt);
    
    // Actions
    void Attack();
    void Run();
    
    // State
    bool IsActive() const { return active_; }
    std::string GetLog() const { return battleLog_; }
    const Monster& GetPlayerMonster() const { return playerMonster_; }
    const Monster& GetEnemyMonster() const { return enemyMonster_; }

private:
    bool active_;
    Monster playerMonster_;
    Monster enemyMonster_;
    std::string battleLog_;
    float turnTimer_;
    bool playerTurn_;
    
    void EnemyTurn();
};

} // namespace engine
