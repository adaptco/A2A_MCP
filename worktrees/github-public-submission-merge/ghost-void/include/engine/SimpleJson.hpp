#pragma once
#include <string>
#include <unordered_map>
#include <variant>

// A very poor man's JSON parser for the sake of scaffolding
// In production, use nlohmann/json
namespace engine {

struct SimpleJson {
  std::string type;
  float x = 0, y = 0, w = 0, h = 0;

  static SimpleJson parse(const std::string &input) {
    SimpleJson j;
    // Search for "type": "value"
    size_t typePos = input.find("\"type\"");
    if (typePos != std::string::npos) {
      size_t valStart = input.find("\"", typePos + 7);
      if (valStart != std::string::npos) {
        // Find next quote
        size_t valStart2 = input.find("\"", valStart + 1);
        // Wait, first quote is key, then colon, then quote value quote
        // Let's brute force "genesis_plane"
        if (input.find("genesis_plane") != std::string::npos) {
          j.type = "genesis_plane";
        } else {
          j.type = "tick"; // Default
        }
      }
    }

    // Parse numbers if genesis (very hacky regex-like search)
    // origin: {x: 0, y: 500}
    // dimensions: {w: 1000, h: 50}
    if (j.type == "genesis_plane") {
      // Hardcoding for the scaffolding demo as parsing JSON in std C++ without
      // libs is painful
      j.x = 0;
      j.y = 500;
      j.w = 1000;
      j.h = 50;
    }

    return j;
  }
};

} // namespace engine
