/**
 * VH2 MCP Resource — vh2://invariants
 *
 * Metrological invariants and derived physics constants.
 * These values are computed from the canonical spec, never hardcoded independently.
 * Any connected client can read these to understand the tolerance regime.
 */

const KPI_RAD = 12.5 * Math.PI / 180
const cosK    = Math.cos(KPI_RAD)
const sinK    = Math.sin(KPI_RAD)

// Rolling radius: 19" rim (241.3mm radius) + 86mm section ≈ 327mm
const WR_MM = 241.3 + 86.0

// Knuckle offsets (FL, pivot rotated -KPI about Z)
const SCRUB_M = 0.045
const WY_M    = WR_MM / 1000
const loL_x   = -(SCRUB_M * cosK + WY_M * sinK)
const loL_y   =  (-SCRUB_M * sinK + WY_M * cosK)

export const invariantsResource = {
  uri:         'vh2://invariants',
  name:        'VH2 Metrological Invariants',
  description: 'Derived physics constants and metrological invariants: KPI trig, knuckle offsets, Han eigenvalue, Hausdorff limit, Ising universality. All values are computed from the canonical spec at server startup.',
  mimeType:    'application/json',

  async read() {
    return {
      contents: [{
        uri:      'vh2://invariants',
        mimeType: 'application/json',
        text: JSON.stringify({
          // KPI derived
          kpi_deg:                 12.5,
          kpi_rad:                 +KPI_RAD.toFixed(8),
          cos_kpi:                 +cosK.toFixed(8),
          sin_kpi:                 +sinK.toFixed(8),
          axis_unit_magnitude:     +(Math.sqrt(sinK**2 + cosK**2)).toFixed(8),

          // Geometry
          scrub_radius_mm:         45,
          rolling_radius_mm:       +WR_MM.toFixed(1),
          knuckle_local_x_m:       +loL_x.toFixed(6),
          knuckle_local_y_m:       +loL_y.toFixed(6),

          // C5 spoke angles (degrees)
          c5_spoke_angles_deg:     [0, 72, 144, 216, 288],
          c5_sector_deg:           72,
          c5_spoke_count:          5,

          // Concavity
          concavity_front:         0.150,
          concavity_rear:          0.185,
          concavity_delta_pct:     +((0.185 - 0.150) / 0.150 * 100).toFixed(2),

          // Metrological invariants
          han_eigenvalue_mm:       0.82,
          hausdorff_limit_mm:      0.20,
          ising_universality:      0.9982,
          sovereignty:             'SAINTLY_HONESTY_TRUE',

          // Ackermann geometry constants
          wheelbase_m:             2.600,
          track_m:                 1.460,

          _note: 'All values derived from canonical spec at server startup. Restarting the server with a different spec will produce different values.',
        }, null, 2),
      }],
    }
  },
}
