#ifndef QUBE_RUNTIME_C_H
#define QUBE_RUNTIME_C_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef void *QubeRuntimeHandle;

typedef struct {
  uint64_t timestamp;
  uint64_t sequence_id;
  const char *previous_hash;
  const char *current_hash;
  const uint8_t *payload;
  int payload_len;
} CTokenPixel;

typedef struct {
  float x, y, w, h;
  char type[64];
} CSyntheticStructure;

QubeRuntimeHandle QubeRuntime_Create();
void QubeRuntime_Destroy(QubeRuntimeHandle handle);

void QubeRuntime_Initialize(QubeRuntimeHandle handle, const char *configHash);
int QubeRuntime_Execute(QubeRuntimeHandle handle, CTokenPixel pixel);

// returns length of hash, copies to buffer up to maxLen (including null
// terminator)
int QubeRuntime_GetStateHash(QubeRuntimeHandle handle, char *buffer,
                             int maxLen);

void QubeRuntime_DockPattern(QubeRuntimeHandle handle, const char *patternId,
                             const uint8_t *data, int dataLen);

int QubeRuntime_ReorganizeAndSynthesize(QubeRuntimeHandle handle,
                                        CSyntheticStructure *structures,
                                        int maxCount);

#ifdef __cplusplus
}
#endif

#endif // QUBE_RUNTIME_C_H
