/**
 * VH2 MCP Tool — vh2_witness
 *
 * Stub tool using z.object({}).passthrough() strategy:
 * accepts any JSON payload and returns a SHA-256 witness hash + tag.
 * Schema is intentionally open — tightened in a future iteration.
 */

import { createHash } from 'crypto'
import { z } from '../schema.js'

// passthrough: accepts any object, no required fields
export const witnessSchema = z.object({}).passthrough()

export async function witnessHandler(params) {
  if (typeof params !== 'object' || params === null) {
    return {
      content: [{ type: 'text', text: 'Error: params must be a JSON object' }],
      isError: true,
    }
  }

  const keys    = Object.keys(params)
  const hex     = createHash('sha256')
    .update(JSON.stringify(params, keys.sort()))
    .digest('hex')
  const tag     = `0xVH2_ET29_ET22_C5_SOV_${hex.slice(0, 6).toUpperCase()}`

  return {
    content: [{
      type: 'text',
      text: JSON.stringify({
        hex,
        tag,
        payload_keys:  keys,
        payload_count: keys.length,
        note: 'SHA-256 over JSON.stringify(payload, sortedKeys). Deterministic — same payload always yields same hash.',
      }, null, 2),
    }],
  }
}

export const witnessTool = {
  name:        'vh2_witness',
  description: 'Generate a SHA-256 witness hash for any JSON payload. Tag format: 0xVH2_ET29_ET22_C5_SOV_{first6hex}. Deterministic — tamper-evident fossil record for any spec object.',
  inputSchema: witnessSchema.toJsonSchema(),  // { type: 'object', additionalProperties: true }
  handler:     witnessHandler,
}
