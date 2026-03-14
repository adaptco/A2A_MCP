#pragma once

#include <vector>
#include <iostream>

namespace engine {

enum class ZoneType { Empty, Residential, Commercial, Industrial, PowerPlant, WaterPump };

struct CityCell {
    ZoneType type;
    int density; // 0-100
    bool hasPower;
    bool hasWater;
};

class CitySimulation {
public:
    CitySimulation(int width, int height);
    
    void Update(float dt);
    
    // Interaction
    void SetZone(int x, int y, ZoneType type);
    const CityCell& GetCell(int x, int y) const;
    int GetPopulation() const;

private:
    int width_;
    int height_;
    std::vector<CityCell> grid_;
    float timer_;
    
    void SimulateResources();
    void SimulateGrowth();
};

} // namespace engine
