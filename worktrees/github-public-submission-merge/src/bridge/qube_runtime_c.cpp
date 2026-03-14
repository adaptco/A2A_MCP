#include "bridge/qube_runtime_c.h"
#include "qube/QubeRuntime.hpp"
#include <algorithm>
#include <cstring>


extern "C" {

QubeRuntimeHandle QubeRuntime_Create() { return new qube::QubeRuntime(); }

void QubeRuntime_Destroy(QubeRuntimeHandle handle) {
  if (handle) {
    delete static_cast<qube::QubeRuntime *>(handle);
  }
}

void QubeRuntime_Initialize(QubeRuntimeHandle handle, const char *configHash) {
  static_cast<qube::QubeRuntime *>(handle)->Initialize(configHash ? configHash
                                                                  : "");
}

int QubeRuntime_Execute(QubeRuntimeHandle handle, CTokenPixel pixel) {
  qube::TokenPixel p;
  p.timestamp = pixel.timestamp;
  p.sequence_id = pixel.sequence_id;
  p.previous_hash = pixel.previous_hash ? pixel.previous_hash : "";
  p.current_hash = pixel.current_hash ? pixel.current_hash : "";
  if (pixel.payload && pixel.payload_len > 0) {
    p.payload.assign(pixel.payload, pixel.payload + pixel.payload_len);
  }

  return static_cast<qube::QubeRuntime *>(handle)->Execute(p) ? 1 : 0;
}

int QubeRuntime_GetStateHash(QubeRuntimeHandle handle, char *buffer,
                             int maxLen) {
  std::string hash = static_cast<qube::QubeRuntime *>(handle)->GetStateHash();
  if (buffer && maxLen > 0) {
    strncpy(buffer, hash.c_str(), maxLen - 1);
    buffer[maxLen - 1] = '\0';
  }
  return hash.length();
}

void QubeRuntime_DockPattern(QubeRuntimeHandle handle, const char *patternId,
                             const uint8_t *data, int dataLen) {
  std::vector<uint8_t> d;
  if (data && dataLen > 0) {
    d.assign(data, data + dataLen);
  }
  static_cast<qube::QubeRuntime *>(handle)->DockPattern(
      patternId ? patternId : "", d);
}

int QubeRuntime_ReorganizeAndSynthesize(QubeRuntimeHandle handle,
                                        CSyntheticStructure *structures,
                                        int maxCount) {
  auto structs =
      static_cast<qube::QubeRuntime *>(handle)->ReorganizeAndSynthesize();
  int count = std::min((int)structs.size(), maxCount);

  if (structures) {
    for (int i = 0; i < count; ++i) {
      structures[i].x = structs[i].x;
      structures[i].y = structs[i].y;
      structures[i].w = structs[i].w;
      structures[i].h = structs[i].h;
      strncpy(structures[i].type, structs[i].type.c_str(),
              sizeof(structures[i].type) - 1);
      structures[i].type[sizeof(structures[i].type) - 1] = '\0';
    }
  }
  return structs.size(); // Return total available count, can be > maxCount
}
}
