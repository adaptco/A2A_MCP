#include "qube/QubeRuntime.hpp"
#include <iostream>
#include <string>
#include <vector>

qube::TokenPixel ParseTokenPixel(const std::string &line) {
  qube::TokenPixel pixel;
  // Basic "poor man's" parsing suited for the expected format

  // Timestamp
  size_t tsPos = line.find("\"timestamp\":");
  if (tsPos != std::string::npos) {
    pixel.timestamp = std::stoull(line.substr(tsPos + 12));
  }

  // Sequence ID
  size_t seqPos = line.find("\"sequence_id\":");
  if (seqPos != std::string::npos) {
    pixel.sequence_id = std::stoull(line.substr(seqPos + 14));
  }

  // Previous Hash
  size_t prevPos = line.find("\"previous_hash\":");
  if (prevPos != std::string::npos) {
    size_t startQuote = line.find("\"", prevPos + 16);
    size_t endQuote = line.find("\"", startQuote + 1);
    if (startQuote != std::string::npos && endQuote != std::string::npos) {
      pixel.previous_hash =
          line.substr(startQuote + 1, endQuote - startQuote - 1);
    }
  }

  // Current Hash
  size_t curPos = line.find("\"current_hash\":");
  if (curPos != std::string::npos) {
    size_t startQuote = line.find("\"", curPos + 15);
    size_t endQuote = line.find("\"", startQuote + 1);
    if (startQuote != std::string::npos && endQuote != std::string::npos) {
      pixel.current_hash =
          line.substr(startQuote + 1, endQuote - startQuote - 1);
    }
  }

  // Payload (Array of bytes) e.g. [222, 173, ...]
  size_t payPos = line.find("\"payload\":");
  if (payPos != std::string::npos) {
    size_t startBracket = line.find("[", payPos);
    size_t endBracket = line.find("]", startBracket);
    if (startBracket != std::string::npos && endBracket != std::string::npos) {
      std::string content =
          line.substr(startBracket + 1, endBracket - startBracket - 1);
      std::string segment;
      size_t subPos = 0;
      while ((subPos = content.find(",")) != std::string::npos) {
        segment = content.substr(0, subPos);
        pixel.payload.push_back(static_cast<uint8_t>(std::stoi(segment)));
        content.erase(0, subPos + 1);
      }
      // Last one
      if (!content.empty()) {
        try {
          pixel.payload.push_back(static_cast<uint8_t>(std::stoi(content)));
        } catch (...) {
        }
      }
    }
  }

  return pixel;
}

int main(int argc, char *argv[]) {
  std::cout << "[QUBE] Starting Kernel..." << std::endl;

  qube::QubeRuntime runtime;
  runtime.Initialize("SHA256:INITIAL_CONFIG_HASH");

  // If arguments provided, maybe file input? For now stdin.
  std::cout << "[QUBE] Waiting for TokenPixels on stdin..." << std::endl;

  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty())
      continue;

    try {
      qube::TokenPixel pixel = ParseTokenPixel(line);

      bool success = runtime.Execute(pixel);
      if (!success) {
        std::cerr << "[QUBE] Execution Failed for pixel " << pixel.sequence_id
                  << std::endl;
        // Decide if we stop or continue. Strict kernel stops?
        // break;
      } else {
        std::cout << "[QUBE] ACK " << pixel.sequence_id << std::endl;
      }

    } catch (const std::exception &e) {
      std::cerr << "[QUBE] Parse Error: " << e.what() << std::endl;
    }
  }

  runtime.Shutdown();
  return 0;
}
