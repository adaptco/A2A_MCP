/**
 * VH2 MCP Resource — vh2://spec
 *
 * The canonical, authoritative VH2 wheel + suspension specification.
 * Clients read this resource to seed tool calls — it is the ground truth
 * that the vh2_validate tool enforces.
 */

import { createHash } from 'crypto'

const SPEC = Object.freeze({
  schema:          'VH2_Full_v1',
  spoke_count:     5,
  rim_diameter_in: 19,
  front_et_mm:     29,
  rear_et_mm:      22,
  kpi_deg:         12.5,
  scrub_radius_mm: 45,
  c5_sector_deg:   72,
  concavity_front: 0.150,
  concavity_rear:  0.185,
  wheelbase_mm:    2600,
  track_mm:        1460,
  material:        'RSM_PBR_D4AF37',
  sovereignty:     'SAINTLY_HONESTY_TRUE',
  han_eigenvalue:  0.82,
  hausdorff_mm:    0.20,
})

const hex = createHash('sha256')
  .update(JSON.stringify(SPEC, Object.keys(SPEC).sort()))
  .digest('hex')

export const specResource = {
  uri:         'vh2://spec',
  name:        'VH2 Canonical Specification',
  description: 'Authoritative VH2 Advan GT Beyond wheel and suspension geometry specification. Contains all 7 fail-closed constraints, physical dimensions, and metrological invariants. Read this before calling vh2_validate.',
  mimeType:    'application/json',

  async read() {
    return {
      contents: [{
        uri:      'vh2://spec',
        mimeType: 'application/json',
        text:     JSON.stringify({
          ...SPEC,
          _witness: {
            hex,
            tag: `0xVH2_ET29_ET22_C5_SOV_${hex.slice(0, 6).toUpperCase()}`,
          },
          _constraints: {
            spoke_count:     5,
            rim_diameter_in: 19,
            front_et_mm:     29,
            rear_et_mm:      22,
            kpi_deg:         12.5,
            scrub_radius_mm: 45,
            c5_sector_deg:   72,
            count:           7,
            enforcement:     'FAIL_CLOSED',
          },
        }, null, 2),
      }],
    }
  },
}
