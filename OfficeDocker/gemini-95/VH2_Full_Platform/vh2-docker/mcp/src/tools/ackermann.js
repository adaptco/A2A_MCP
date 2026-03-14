/**
 * VH2 MCP Tool — vh2_ackermann
 *
 * Computes Ackermann-corrected inner/outer steer angles for a given
 * steering input. Returns inner_deg, outer_deg, delta_deg, turn_radius_m.
 */

import { z } from '../schema.js'

export const ackermannSchema = z.object({
  steer_deg: z.number().min(-45).max(45)
    .describe('Steering input angle in degrees [-45, 45]'),
  wheelbase_mm: z.number().optional()
    .describe('Wheelbase in mm (default: 2600)'),
  track_mm: z.number().optional()
    .describe('Track width in mm (default: 1460)'),
})

export async function ackermannHandler(params) {
  const parsed = ackermannSchema.safeParse(params)
  if (!parsed.success) {
    return { content: [{ type: 'text', text: `Schema error: ${parsed.error}` }], isError: true }
  }

  const { steer_deg, wheelbase_mm = 2600, track_mm = 1460 } = parsed.data

  if (Math.abs(steer_deg) < 0.05) {
    return {
      content: [{ type: 'text', text: JSON.stringify({
        steer_deg, inner_deg: 0, outer_deg: 0,
        delta_deg: 0, turn_radius_m: null,
        description: 'Straight ahead — no Ackermann correction needed',
      }, null, 2) }],
    }
  }

  const sign = Math.sign(steer_deg)
  const d    = Math.abs(steer_deg) * Math.PI / 180
  const L    = wheelbase_mm / 1000
  const T    = track_mm    / 1000
  const R    = L / Math.tan(d)

  const inner = Math.atan(L / (R - T / 2)) * sign
  const outer = Math.atan(L / (R + T / 2)) * sign

  const result = {
    steer_deg,
    inner_deg:      +(inner * 180 / Math.PI).toFixed(4),
    outer_deg:      +(outer * 180 / Math.PI).toFixed(4),
    delta_deg:      +((Math.abs(inner) - Math.abs(outer)) * 180 / Math.PI).toFixed(4),
    turn_radius_m:  +R.toFixed(3),
    wheelbase_mm,
    track_mm,
    description: `At ${steer_deg}°: inner wheel steers ${(Math.abs(inner)*180/Math.PI).toFixed(2)}°, outer steers ${(Math.abs(outer)*180/Math.PI).toFixed(2)}° (Ackermann Δ = ${((Math.abs(inner)-Math.abs(outer))*180/Math.PI).toFixed(3)}°)`,
  }

  return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] }
}

export const ackermannTool = {
  name:        'vh2_ackermann',
  description: 'Compute Ackermann-corrected steering angles. Inner wheel always turns tighter than outer for correct low-scrub geometry. Returns inner_deg, outer_deg, delta_deg, and turn_radius_m.',
  inputSchema: ackermannSchema.toJsonSchema(),
  handler:     ackermannHandler,
}
