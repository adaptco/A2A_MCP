'use strict'
/**
 * VH2 Backend Socket — Server-side Unit Tests
 * Run: node tests/validator.test.js
 */

const crypto = require('crypto')

let pass = 0, fail = 0

function assert(desc, actual, expected) {
  const ok = actual === expected
  console.log(`  ${ok ? '✓' : '✗'} ${desc}`)
  if (!ok) console.log(`      expected: ${expected}\n      got:      ${actual}`)
  ok ? pass++ : fail++
}

function assertNear(desc, actual, expected, tol = 0.0001) {
  const ok = Math.abs(actual - expected) <= tol
  console.log(`  ${ok ? '✓' : '✗'} ${desc}`)
  if (!ok) console.log(`      expected: ${expected} ±${tol}\n      got:      ${actual}`)
  ok ? pass++ : fail++
}

// ── Inline the functions under test ────────────────────────────────────────
const VH2_SPEC = Object.freeze({
  schema:'VH2_Full_v1', spoke_count:5, rim_diameter_in:19,
  front_et_mm:29, rear_et_mm:22, kpi_deg:12.5, scrub_radius_mm:45,
  c5_sector_deg:72, concavity_front:0.150, concavity_rear:0.185,
  wheelbase_mm:2600, track_mm:1460, material:'RSM_PBR_D4AF37',
  sovereignty:'SAINTLY_HONESTY_TRUE', han_eigenvalue:0.82, hausdorff_mm:0.20,
})

const CONSTRAINTS = Object.freeze({
  spoke_count:5, rim_diameter_in:19, front_et_mm:29, rear_et_mm:22,
  kpi_deg:12.5, scrub_radius_mm:45, c5_sector_deg:72,
})

function witnessHash(payload) {
  return crypto.createHash('sha256')
    .update(JSON.stringify(payload, Object.keys(payload).sort()))
    .digest('hex')
}

function witnessTag(hex) { return `0xVH2_ET29_ET22_C5_SOV_${hex.slice(0,6).toUpperCase()}` }

function validate(spec) {
  const errors = []
  for (const [k,v] of Object.entries(CONSTRAINTS)) {
    if (spec[k] !== v) errors.push({ key:k, expected:v, got:spec[k] })
  }
  if (errors.length > 0) return { pass:false, status:'SYSTEM_HALT', violations:errors }
  const hex = witnessHash(spec)
  return { pass:true, status:'SOVEREIGN_PASS', witness:{ hex, tag:witnessTag(hex) } }
}

const KPI_RAD = 12.5 * Math.PI / 180
const cosK = Math.cos(KPI_RAD), sinK = Math.sin(KPI_RAD)
const WB = 2600/1000, TRACK = 1460/1000, SCRUB = 45/1000

function ackermann(deg) {
  if (Math.abs(deg) < 0.05) return { inner_deg:0, outer_deg:0, delta_deg:0 }
  const sign = Math.sign(deg), d = Math.abs(deg)*Math.PI/180
  const R = WB/Math.tan(d)
  const inner = Math.atan(WB/(R-TRACK/2))*sign
  const outer = Math.atan(WB/(R+TRACK/2))*sign
  return {
    inner_deg: +(inner*180/Math.PI).toFixed(4),
    outer_deg: +(outer*180/Math.PI).toFixed(4),
    delta_deg: +((Math.abs(inner)-Math.abs(outer))*180/Math.PI).toFixed(4),
    turn_radius_m: +(R).toFixed(3),
  }
}

// ── TEST SUITES ─────────────────────────────────────────────────────────────

console.log('\n[1] CANONICAL SPEC')
assert('schema = VH2_Full_v1',        VH2_SPEC.schema, 'VH2_Full_v1')
assert('spoke_count = 5',             VH2_SPEC.spoke_count, 5)
assert('rim_diameter_in = 19',        VH2_SPEC.rim_diameter_in, 19)
assert('front_et_mm = 29',            VH2_SPEC.front_et_mm, 29)
assert('rear_et_mm = 22',             VH2_SPEC.rear_et_mm, 22)
assert('kpi_deg = 12.5',              VH2_SPEC.kpi_deg, 12.5)
assert('scrub_radius_mm = 45',        VH2_SPEC.scrub_radius_mm, 45)
assert('sovereignty = SAINTLY_HONESTY_TRUE', VH2_SPEC.sovereignty, 'SAINTLY_HONESTY_TRUE')

console.log('\n[2] FAIL-CLOSED VALIDATOR')
const okResult = validate(VH2_SPEC)
assert('valid spec → SOVEREIGN_PASS', okResult.status, 'SOVEREIGN_PASS')
assert('valid spec → pass=true',      okResult.pass, true)
const tampers = [
  {spoke_count:4}, {rim_diameter_in:18}, {front_et_mm:35},
  {rear_et_mm:25}, {kpi_deg:10}, {scrub_radius_mm:30}, {c5_sector_deg:60}
]
tampers.forEach(t => {
  const res = validate({...VH2_SPEC, ...t})
  assert(`tamper ${Object.keys(t)[0]}=${Object.values(t)[0]} → SYSTEM_HALT`, res.status, 'SYSTEM_HALT')
  assert(`tamper ${Object.keys(t)[0]} → pass=false`, res.pass, false)
})

console.log('\n[3] SHA-256 WITNESS')
const hex1 = witnessHash(VH2_SPEC)
const hex2 = witnessHash(VH2_SPEC)
assert('hex length = 64',         hex1.length, 64)
assert('deterministic (same→same)', hex1, hex2)
const hexTampered = witnessHash({...VH2_SPEC, spoke_count:4})
assert('tampered hash differs',   hex1 !== hexTampered, true)
const tag = witnessTag(hex1)
assert('tag starts with 0xVH2_ET29', tag.startsWith('0xVH2_ET29'), true)
assert('tag length = 29',         tag.length, 29)  // '0xVH2_ET29_ET22_C5_SOV_' (23) + 6 hex = 29

console.log('\n[4] ACKERMANN GEOMETRY')
const a0 = ackermann(0.04)
assert('At 0°: inner=0',  a0.inner_deg, 0)
assert('At 0°: outer=0',  a0.outer_deg, 0)
const a10 = ackermann(10)
assert('At 10°: inner > outer', a10.inner_deg > a10.outer_deg, true)
assert('At 10°: delta > 0',     a10.delta_deg > 0, true)
const a35 = ackermann(35)
assert('At 35°: inner > outer', a35.inner_deg > a35.outer_deg, true)
assert('At 35°: delta > 3°',    a35.delta_deg > 3.0, true)
const aN  = ackermann(-15)
assert('Negative steer: inner < 0',  aN.inner_deg < 0, true)
assert('Negative steer: |i|>|o|',   Math.abs(aN.inner_deg) > Math.abs(aN.outer_deg), true)

console.log('\n[5] KPI KINEMATICS')
assertNear('cos(KPI) = 0.97630', cosK, 0.97630, 0.0001)
assertNear('sin(KPI) = 0.21644', sinK, 0.21644, 0.0001)
assertNear('axis magnitude = 1', Math.sqrt(sinK**2 + cosK**2), 1.0, 0.000001)
const WY = (1.205+0.430)  // rolling radius in metres equivalent
const loL_x = -SCRUB*cosK - WY*sinK
const loL_y = -SCRUB*sinK + WY*cosK
assert('knuckle local X < 0 (FL side)', loL_x < 0, true)
assert('knuckle local Y > 0 (above ground)', loL_y > 0, true)

// ── SUMMARY ─────────────────────────────────────────────────────────────────
console.log(`\n${'─'.repeat(50)}`)
console.log(`RESULT: ${pass} passed, ${fail} failed`)
if (fail > 0) { console.log('STATUS: ✗ SYSTEM HALT — CONSTRAINTS VIOLATED'); process.exit(1) }
else          { console.log('STATUS: ✓ SOVEREIGN PASS — ALL CONSTRAINTS MET'); process.exit(0) }
