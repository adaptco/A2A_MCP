/**
 * VH2 MCP Tool — vh2_validate
 *
 * Accepts a geometry spec object and runs the 7 fail-closed constraints.
 * Returns SOVEREIGN_PASS + SHA-256 witness tag, or SYSTEM_HALT + violations.
 */

import { createHash } from 'crypto'
import { z } from '../schema.js'

// ── SCHEMA (typed — real validation, not passthrough) ──────────────────────
export const validateSchema = z.object({
  spoke_count:     z.number().describe('Number of wheel spokes (must be 5)'),
  rim_diameter_in: z.number().describe('Rim diameter in inches (must be 19)'),
  front_et_mm:     z.number().describe('Front wheel ET offset in mm (must be 29)'),
  rear_et_mm:      z.number().describe('Rear wheel ET offset in mm (must be 22)'),
  kpi_deg:         z.number().describe('Kingpin inclination angle in degrees (must be 12.5)'),
  scrub_radius_mm: z.number().describe('Scrub radius in mm (must be 45)'),
  c5_sector_deg:   z.number().describe('C5 spoke sector spacing in degrees (must be 72)'),
}).passthrough()  // allow extra fields (e.g. schema, wheelbase_mm) without error

// ── CONSTRAINTS ────────────────────────────────────────────────────────────
const CONSTRAINTS = Object.freeze({
  spoke_count:     5,
  rim_diameter_in: 19,
  front_et_mm:     29,
  rear_et_mm:      22,
  kpi_deg:         12.5,
  scrub_radius_mm: 45,
  c5_sector_deg:   72,
})

function witnessHash(payload) {
  return createHash('sha256')
    .update(JSON.stringify(payload, Object.keys(payload).sort()))
    .digest('hex')
}

// ── HANDLER ────────────────────────────────────────────────────────────────
export async function validateHandler(params) {
  // Schema parse (coerces numbers, rejects missing required fields)
  const parsed = validateSchema.safeParse(params)
  if (!parsed.success) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          pass:    false,
          status:  'SCHEMA_ERROR',
          error:   parsed.error,
        }, null, 2),
      }],
      isError: true,
    }
  }

  const spec       = parsed.data
  const violations = []

  for (const [key, expected] of Object.entries(CONSTRAINTS)) {
    if (spec[key] !== expected) {
      violations.push({ key, expected, got: spec[key] })
    }
  }

  if (violations.length > 0) {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          pass:       false,
          status:     'SYSTEM_HALT',
          violations,
          checked:    Object.keys(CONSTRAINTS).length,
        }, null, 2),
      }],
      isError: true,
    }
  }

  const hex = witnessHash(spec)
  const tag = `0xVH2_ET29_ET22_C5_SOV_${hex.slice(0, 6).toUpperCase()}`

  return {
    content: [{
      type: 'text',
      text: JSON.stringify({
        pass:    true,
        status:  'SOVEREIGN_PASS',
        checked: Object.keys(CONSTRAINTS).length,
        witness: { hex, tag },
      }, null, 2),
    }],
  }
}

export const validateTool = {
  name:        'vh2_validate',
  description: 'Fail-closed constraint validator for the VH2 Advan GT Beyond wheel specification. Returns SOVEREIGN_PASS + SHA-256 witness, or SYSTEM_HALT + violation list.',
  inputSchema: validateSchema.toJsonSchema(),
  handler:     validateHandler,
}
