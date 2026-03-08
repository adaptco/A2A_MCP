#include "engine/MonsterBattle.hpp"
#include <iostream>

namespace engine {

BattleSystem::BattleSystem() : active_(false), turnTimer_(0), playerTurn_(true) {}

void BattleSystem::StartBattle(const Monster& playerMonster, const Monster& enemyMonster) {
    playerMonster_ = playerMonster;
    enemyMonster_ = enemyMonster;
    active_ = true;
    playerTurn_ = true;
    battleLog_ = "A wild " + enemyMonster_.name + " appeared!";
}

void BattleSystem::Update(float dt) {
    if (!active_) return;

    if (!playerTurn_) {
        turnTimer_ += dt;
        if (turnTimer_ > 1.5f) { // Enemy thinks for 1.5s
            EnemyTurn();
            turnTimer_ = 0;
            playerTurn_ = true;
        }
    }
}

void BattleSystem::Attack() {
    if (!active_ || !playerTurn_) return;

    int damage = playerMonster_.attack;
    enemyMonster_.hp -= damage;
    battleLog_ = playerMonster_.name + " used Tackle! " + std::to_string(damage) + " damage.";
    
    if (enemyMonster_.hp <= 0) {
        enemyMonster_.hp = 0;
        active_ = false;
        battleLog_ += " You won!";
    } else {
        playerTurn_ = false;
    }
}

void BattleSystem::Run() {
    if (!active_) return;
    active_ = false;
    battleLog_ = "Got away safely!";
}

void BattleSystem::EnemyTurn() {
    int damage = enemyMonster_.attack;
    playerMonster_.hp -= damage;
    battleLog_ = enemyMonster_.name + " used Scratch! " + std::to_string(damage) + " damage.";

    if (playerMonster_.hp <= 0) {
        playerMonster_.hp = 0;
        active_ = false;
        battleLog_ += " You blacked out!";
    }
}

} // namespace engine
