'use strict'

/**
 * VH2 BACKEND SOCKET — Express.js API Server
 * 
 * Socket role: receives geometry spec from frontend socket,
 * runs fail-closed validation, returns SHA-256 witness hash.
 *
 * Endpoints:
 *   GET  /health              — liveness probe (Docker HEALTHCHECK)
 *   GET  /api/spec            — returns canonical VH2 spec
 *   POST /api/validate        — fail-closed constraint validator
 *   POST /api/witness         — SHA-256 witness hash generator
 *   GET  /api/ackermann/:deg  — Ackermann geometry at given steer angle
 *   GET  /api/kpi             — kingpin invariants
 */

const express = require('express')
const cors    = require('cors')
const helmet  = require('helmet')
const crypto  = require('crypto')

const app  = express()
const PORT = process.env.PORT || 3001
const HOST = process.env.HOST || '0.0.0.0'

// ── MIDDLEWARE ──────────────────────────────────────────────────────────────
app.use(helmet({ contentSecurityPolicy: false }))
app.use(cors({ origin: process.env.ALLOWED_ORIGIN || '*' }))
app.use(express.json())
app.use((req, _res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`)
  next()
})

// ── CANONICAL SPEC (ground truth, backend authoritative) ───────────────────
const VH2_SPEC = Object.freeze({
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

// ── CONSTRAINTS (fail-closed) ──────────────────────────────────────────────
const CONSTRAINTS = Object.freeze({
  spoke_count:     5,
  rim_diameter_in: 19,
  front_et_mm:     29,
  rear_et_mm:      22,
  kpi_deg:         12.5,
  scrub_radius_mm: 45,
  c5_sector_deg:   72,
})

// ── KPI PHYSICS ────────────────────────────────────────────────────────────
const KPI_RAD = VH2_SPEC.kpi_deg * Math.PI / 180
const cosK    = Math.cos(KPI_RAD)
const sinK    = Math.sin(KPI_RAD)
const SCRUB   = VH2_SPEC.scrub_radius_mm / 1000  // metres
const WB      = VH2_SPEC.wheelbase_mm / 1000
const TRACK   = VH2_SPEC.track_mm / 1000

// ── SHA-256 WITNESS ────────────────────────────────────────────────────────
function witnessHash(payload) {
  return crypto
    .createHash('sha256')
    .update(JSON.stringify(payload, Object.keys(payload).sort()))
    .digest('hex')
}

function witnessTag(hex) {
  return `0xVH2_ET29_ET22_C5_SOV_${hex.slice(0, 6).toUpperCase()}`
}

// ── ACKERMANN GEOMETRY ─────────────────────────────────────────────────────
function ackermann(steerDeg) {
  if (Math.abs(steerDeg) < 0.05) {
    return { inner_deg: 0, outer_deg: 0, delta_deg: 0, turn_radius_m: Infinity }
  }
  const sign = Math.sign(steerDeg)
  const d    = Math.abs(steerDeg) * Math.PI / 180
  const R    = WB / Math.tan(d)
  const inner = Math.atan(WB / (R - TRACK / 2)) * sign
  const outer = Math.atan(WB / (R + TRACK / 2)) * sign
  return {
    input_deg:      steerDeg,
    inner_deg:      +(inner * 180 / Math.PI).toFixed(4),
    outer_deg:      +(outer * 180 / Math.PI).toFixed(4),
    delta_deg:      +((Math.abs(inner) - Math.abs(outer)) * 180 / Math.PI).toFixed(4),
    turn_radius_m:  +(R).toFixed(3),
  }
}

// ── METRICS (in-process counters, zero new deps) ────────────────────────────
const _m = {
  validate_total: 0, sovereign_pass: 0, system_halt: 0, validate_error: 0,
  halt_by_key:    {},      // { spoke_count: 3, … }
  lat_buckets:    { 1:0, 5:0, 10:0, 25:0, 50:0, 100:0, Inf:0 },
  lat_sum:        0,
  lat_count:      0,
  ep:             { health:0, spec:0, validate:0, witness:0, ackermann:0, kpi:0 },
  started_ms:     Date.now(),
}

function _recordLatency(ms) {
  _m.lat_sum += ms; _m.lat_count++
  for (const le of [1, 5, 10, 25, 50, 100]) { if (ms <= le) _m.lat_buckets[le]++ }
  _m.lat_buckets.Inf++
}

function _renderMetrics() {
  const up = Date.now() - _m.started_ms
  const L  = []
  const h  = (name, help, type) => L.push(`# HELP ${name} ${help}`, `# TYPE ${name} ${type}`)

  h('vh2_validator_requests_total', 'Total POST /api/validate calls.', 'counter')
  L.push(
    `vh2_validator_requests_total{result="sovereign_pass"} ${_m.sovereign_pass}`,
    `vh2_validator_requests_total{result="system_halt"} ${_m.system_halt}`,
    `vh2_validator_requests_total{result="error"} ${_m.validate_error}`,
  )

  h('vh2_validator_system_halt_total', 'Halt events broken down by violated constraint key.', 'counter')
  for (const [k, n] of Object.entries(_m.halt_by_key)) {
    L.push(`vh2_validator_system_halt_total{constraint="${k}"} ${n}`)
  }
  if (!Object.keys(_m.halt_by_key).length) L.push('# (no halts recorded yet)')

  L.push(
    '# HELP vh2_validator_latency_ms Latency of POST /api/validate in milliseconds.',
    '# TYPE vh2_validator_latency_ms histogram',
  )
  for (const le of [1, 5, 10, 25, 50, 100]) {
    L.push(`vh2_validator_latency_ms_bucket{le="${le}"} ${_m.lat_buckets[le]}`)
  }
  L.push(
    `vh2_validator_latency_ms_bucket{le="+Inf"} ${_m.lat_buckets.Inf}`,
    `vh2_validator_latency_ms_sum ${_m.lat_sum.toFixed(3)}`,
    `vh2_validator_latency_ms_count ${_m.lat_count}`,
  )

  h('vh2_endpoint_requests_total', 'Request counts by endpoint.', 'counter')
  for (const [ep, n] of Object.entries(_m.ep)) {
    L.push(`vh2_endpoint_requests_total{endpoint="${ep}"} ${n}`)
  }

  h('vh2_process_uptime_ms', 'Milliseconds since process start.', 'gauge')
  L.push(`vh2_process_uptime_ms ${up}`)

  return L.join('\n') + '\n'
}

// ── VALIDATE SPEC ──────────────────────────────────────────────────────────
function validate(spec) {
  const errors = []
  for (const [key, expected] of Object.entries(CONSTRAINTS)) {
    if (spec[key] !== expected) {
      errors.push({ key, expected, got: spec[key], status: 'CONSTRAINT_VIOLATION' })
    }
  }
  if (errors.length > 0) {
    return { pass: false, status: 'SYSTEM_HALT', violations: errors, checked: Object.keys(CONSTRAINTS).length }
  }
  const hex = witnessHash(spec)
  return {
    pass:    true,
    status:  'SOVEREIGN_PASS',
    checked: Object.keys(CONSTRAINTS).length,
    witness: { hex, tag: witnessTag(hex) },
  }
}

// ── ROUTES ─────────────────────────────────────────────────────────────────

// GET /health
app.get('/health', (_req, res) => {
  _m.ep.health++
  res.json({
    status:    'UP',
    service:   'vh2-backend-socket',
    timestamp: new Date().toISOString(),
    uptime_s:  Math.floor(process.uptime()),
    spec:      VH2_SPEC.schema,
  })
})

// GET /api/spec
app.get('/api/spec', (_req, res) => {
  _m.ep.spec++
  const hex = witnessHash(VH2_SPEC)
  res.json({
    spec:    VH2_SPEC,
    witness: { hex, tag: witnessTag(hex) },
    constraints: Object.keys(CONSTRAINTS).length,
  })
})

// POST /api/validate  { ...spec fields }
app.post('/api/validate', (req, res) => {
  _m.ep.validate++
  _m.validate_total++
  const t0 = Date.now()
  let result
  try {
    result = validate(req.body)
  } catch (err) {
    _m.validate_error++
    return res.status(500).json({ error: err.message })
  }
  const ms = Date.now() - t0
  _recordLatency(ms)
  if (result.pass) {
    _m.sovereign_pass++
  } else {
    _m.system_halt++
    for (const v of result.violations ?? []) {
      _m.halt_by_key[v.key] = (_m.halt_by_key[v.key] || 0) + 1
    }
  }
  res.status(result.pass ? 200 : 422).json(result)
})

// POST /api/witness  { any object }
app.post('/api/witness', (req, res) => {
  _m.ep.witness++
  const hex = witnessHash(req.body)
  res.json({ hex, tag: witnessTag(hex), payload_keys: Object.keys(req.body) })
})

// GET /api/ackermann/:deg
app.get('/api/ackermann/:deg', (req, res) => {
  _m.ep.ackermann++
  const deg = parseFloat(req.params.deg)
  if (isNaN(deg) || Math.abs(deg) > 45) {
    return res.status(400).json({ error: 'steer_deg must be a number in [-45, 45]' })
  }
  res.json(ackermann(deg))
})

// GET /api/kpi
app.get('/api/kpi', (_req, res) => {
  _m.ep.kpi++
  const loL_x = -SCRUB * cosK - (VH2_SPEC.track_mm / 2000) * sinK
  const loL_y = -SCRUB * sinK + (VH2_SPEC.track_mm / 2000) * cosK
  res.json({
    kpi_deg:       VH2_SPEC.kpi_deg,
    kpi_rad:       +KPI_RAD.toFixed(6),
    cos_kpi:       +cosK.toFixed(6),
    sin_kpi:       +sinK.toFixed(6),
    scrub_m:       SCRUB,
    wheelbase_m:   WB,
    track_m:       TRACK,
    knuckle_local: { x: +loL_x.toFixed(4), y: +loL_y.toFixed(4) },
    han_eigenvalue_mm: VH2_SPEC.han_eigenvalue,
    hausdorff_limit_mm: VH2_SPEC.hausdorff_mm,
    axis_unit_magnitude: +(Math.sqrt(sinK ** 2 + cosK ** 2)).toFixed(6),
  })
})

// ── METRICS ───────────────────────────────────────────────────────────────────
// Prometheus text format. Safe to scrape at any interval — pure in-process state.
// Does NOT appear in /health JSON so existing consumers are unaffected.
app.get('/metrics', (_req, res) => {
  res.setHeader('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
  res.send(_renderMetrics())
})

// ── 404 HANDLER ────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({ error: 'Not found', path: req.path })
})

// ── START ──────────────────────────────────────────────────────────────────
app.listen(PORT, HOST, () => {
  console.log(`VH2 Backend Socket listening on ${HOST}:${PORT}`)
  console.log(`Spec:    ${VH2_SPEC.schema}`)
  console.log(`Witness: ${witnessTag(witnessHash(VH2_SPEC))}`)
})

module.exports = app
