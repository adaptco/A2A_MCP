#include "engine/CitySimulation.hpp"
#include <algorithm>

namespace engine {

CitySimulation::CitySimulation(int width, int height) 
    : width_(width), height_(height), timer_(0) {
    grid_.resize(width * height, {ZoneType::Empty, 0, false, false});
}

void CitySimulation::Update(float dt) {
    timer_ += dt;
    if (timer_ > 1.0f) { // Sim tick every second
        timer_ = 0;
        SimulateResources();
        SimulateGrowth();
    }
}

void CitySimulation::SetZone(int x, int y, ZoneType type) {
    if (x >= 0 && x < width_ && y >= 0 && y < height_) {
        grid_[y * width_ + x].type = type;
        if (type == ZoneType::Empty) grid_[y * width_ + x].density = 0;
    }
}

const CityCell& CitySimulation::GetCell(int x, int y) const {
    static CityCell empty = {ZoneType::Empty, 0, false, false};
    if (x >= 0 && x < width_ && y >= 0 && y < height_) {
        return grid_[y * width_ + x];
    }
    return empty;
}

int CitySimulation::GetPopulation() const {
    int pop = 0;
    for (const auto& cell : grid_) {
        if (cell.type == ZoneType::Residential) {
            pop += cell.density;
        }
    }
    return pop;
}

void CitySimulation::SimulateResources() {
    // Reset resources
    for (auto& cell : grid_) {
        cell.hasPower = false;
        cell.hasWater = false;
    }

    // Flood fill power from PowerPlants (simplified distance check for now)
    for (int y = 0; y < height_; ++y) {
        for (int x = 0; x < width_; ++x) {
            if (grid_[y * width_ + x].type == ZoneType::PowerPlant) {
                // Power plants power 5 radius
                for (int dy = -5; dy <= 5; ++dy) {
                    for (int dx = -5; dx <= 5; ++dx) {
                        int nx = x + dx;
                        int ny = y + dy;
                        if (nx >= 0 && nx < width_ && ny >= 0 && ny < height_) {
                            grid_[ny * width_ + nx].hasPower = true;
                        }
                    }
                }
            }
        }
    }
}

void CitySimulation::SimulateGrowth() {
    for (auto& cell : grid_) {
        if (cell.type == ZoneType::Residential) {
            if (cell.hasPower && cell.density < 100) {
                cell.density++;
            } else if (!cell.hasPower && cell.density > 0) {
                cell.density--;
            }
        }
    }
}

} // namespace engine
