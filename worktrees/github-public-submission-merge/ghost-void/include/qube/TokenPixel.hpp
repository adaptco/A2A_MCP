#pragma once

#include <vector>
#include <cstdint>
#include <string>

namespace qube {

struct TokenPixel {
    uint64_t timestamp;
    uint64_t sequence_id;
    std::string previous_hash;
    std::string current_hash;
    std::vector<uint8_t> payload; // The encoded state
    // Metadata can be added here
};

} // namespace qube
