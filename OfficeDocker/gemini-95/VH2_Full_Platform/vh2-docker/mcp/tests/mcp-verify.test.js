#!/usr/bin/env node
/**
 * VH2 MCP — Verification Test Script
 *
 * Gold-standard MCP handshake verification:
 *   1. Spawns the server as a child process (stdin/stdout pipe)
 *   2. Sends initialize → tools/list → resources/list
 *   3. Calls each tool with representative inputs
 *   4. Reads each resource
 *   5. Reports pass/fail for every assertion
 *
 * Usage:
 *   node tests/mcp-verify.test.js
 *   npm test
 */

import { spawn }        from 'child_process'
import { createInterface } from 'readline'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'

const __dir    = dirname(fileURLToPath(import.meta.url))
const INDEX_JS = join(__dir, '..', 'src', 'index.js')

// ── Test framework ──────────────────────────────────────────────────────────
let pass = 0, fail = 0, idSeq = 1
const t0 = Date.now()

function ok(desc, val) {
  if (val) {
    console.log(`  ✓ ${desc}`)
    pass++
  } else {
    console.log(`  ✗ ${desc}`)
    fail++
  }
}
function section(name) { console.log(`\n[${name}]`) }

// ── Server process + request/response machinery ─────────────────────────────
function spawnServer() {
  const proc = spawn('node', [INDEX_JS], {
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  // stderr → our stderr (server logs)
  proc.stderr.on('data', d => process.stderr.write(`  ${d}`))

  const pending = new Map()   // id → { resolve, reject }

  const rl = createInterface({ input: proc.stdout, terminal: false })
  rl.on('line', line => {
    let msg
    try { msg = JSON.parse(line.trim()) } catch { return }
    if (msg.id !== undefined && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id)
      pending.delete(msg.id)
      if (msg.error) reject(Object.assign(new Error(msg.error.message), msg.error))
      else           resolve(msg.result)
    }
  })

  function request(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = idSeq++
      pending.set(id, { resolve, reject })
      proc.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n')
      // timeout
      setTimeout(() => {
        if (pending.has(id)) {
          pending.delete(id)
          reject(new Error(`Timeout: ${method}`))
        }
      }, 5000)
    })
  }

  function notify(method, params = {}) {
    proc.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n')
  }

  function stop() { proc.stdin.end(); proc.kill() }

  return { request, notify, stop, proc }
}

// ── TEST SUITES ─────────────────────────────────────────────────────────────
async function run() {
  console.log('VH2 MCP — Verification Test Suite')
  console.log('StdioServerTransport · JSON-RPC 2.0 · MCP 2024-11-05')

  const { request, notify, stop } = spawnServer()

  // Small delay for server startup
  await new Promise(r => setTimeout(r, 200))

  try {

    // ── [1] INITIALIZE HANDSHAKE ────────────────────────────────────────
    section('1 — INITIALIZE HANDSHAKE')
    const init = await request('initialize', {
      protocolVersion: '2024-11-05',
      clientInfo: { name: 'vh2-test-client', version: '1.0.0' },
      capabilities: {},
    })
    ok('initialize returns result',                   !!init)
    ok('protocolVersion present',                     !!init?.protocolVersion)
    ok('serverInfo.name present',                     !!init?.serverInfo?.name)
    ok('serverInfo.version present',                  !!init?.serverInfo?.version)
    ok('capabilities.tools present',                  !!init?.capabilities?.tools)
    ok('capabilities.resources present',              !!init?.capabilities?.resources)

    notify('notifications/initialized')
    await new Promise(r => setTimeout(r, 50))

    // ── [2] TOOLS/LIST ──────────────────────────────────────────────────
    section('2 — TOOLS/LIST')
    const { tools } = await request('tools/list')
    ok('tools/list returns array',                    Array.isArray(tools))
    ok('exactly 4 tools registered',                  tools?.length === 4)

    const toolNames = tools?.map(t => t.name) ?? []
    ok('vh2_validate registered',                     toolNames.includes('vh2_validate'))
    ok('vh2_ackermann registered',                    toolNames.includes('vh2_ackermann'))
    ok('vh2_kpi registered',                          toolNames.includes('vh2_kpi'))
    ok('vh2_witness registered',                      toolNames.includes('vh2_witness'))

    // Every tool must have name, description, inputSchema
    tools?.forEach(t => {
      ok(`${t.name} has description`,                 !!t.description)
      ok(`${t.name} has inputSchema`,                 !!t.inputSchema)
      ok(`${t.name} inputSchema.type = 'object'`,     t.inputSchema?.type === 'object')
    })

    // passthrough stub: vh2_witness must have additionalProperties:true
    const witnessDef = tools?.find(t => t.name === 'vh2_witness')
    ok('vh2_witness inputSchema.additionalProperties = true (passthrough)',
      witnessDef?.inputSchema?.additionalProperties === true)

    // Typed tools must have required fields
    const validateDef = tools?.find(t => t.name === 'vh2_validate')
    ok('vh2_validate has required fields array',
      Array.isArray(validateDef?.inputSchema?.required))
    ok('vh2_validate requires spoke_count',
      validateDef?.inputSchema?.required?.includes('spoke_count'))

    // ── [3] RESOURCES/LIST ──────────────────────────────────────────────
    section('3 — RESOURCES/LIST')
    const { resources } = await request('resources/list')
    ok('resources/list returns array',                Array.isArray(resources))
    ok('exactly 3 resources registered',              resources?.length === 3)

    const resourceURIs = resources?.map(r => r.uri) ?? []
    ok('vh2://spec registered',                       resourceURIs.includes('vh2://spec'))
    ok('vh2://invariants registered',                 resourceURIs.includes('vh2://invariants'))
    ok('vh2://deploy registered',                     resourceURIs.includes('vh2://deploy'))

    resources?.forEach(r => {
      ok(`${r.uri} has name`,                         !!r.name)
      ok(`${r.uri} has description`,                  !!r.description)
      ok(`${r.uri} mimeType = application/json`,      r.mimeType === 'application/json')
    })

    // ── [4] TOOL CALLS ──────────────────────────────────────────────────
    section('4a — TOOLS/CALL: vh2_validate (SOVEREIGN_PASS)')
    const vPass = await request('tools/call', {
      name: 'vh2_validate',
      arguments: {
        spoke_count:5, rim_diameter_in:19, front_et_mm:29,
        rear_et_mm:22, kpi_deg:12.5, scrub_radius_mm:45, c5_sector_deg:72,
      },
    })
    const vPassData = JSON.parse(vPass?.content?.[0]?.text ?? '{}')
    ok('validate call returns content',               !!vPass?.content)
    ok('validate SOVEREIGN_PASS: pass=true',          vPassData.pass === true)
    ok('validate SOVEREIGN_PASS: status=SOVEREIGN_PASS', vPassData.status === 'SOVEREIGN_PASS')
    ok('validate SOVEREIGN_PASS: witness.hex present',  !!vPassData.witness?.hex)
    ok('validate SOVEREIGN_PASS: witness.hex length=64', vPassData.witness?.hex?.length === 64)
    ok('validate SOVEREIGN_PASS: witness.tag present',  !!vPassData.witness?.tag)
    ok('validate SOVEREIGN_PASS: tag starts 0xVH2_ET29',
      vPassData.witness?.tag?.startsWith('0xVH2_ET29'))
    ok('validate SOVEREIGN_PASS: isError absent',    !vPass?.isError)

    section('4b — TOOLS/CALL: vh2_validate (SYSTEM_HALT — tampered spoke_count=4)')
    const vFail = await request('tools/call', {
      name: 'vh2_validate',
      arguments: {
        spoke_count:4, rim_diameter_in:19, front_et_mm:29,
        rear_et_mm:22, kpi_deg:12.5, scrub_radius_mm:45, c5_sector_deg:72,
      },
    })
    const vFailData = JSON.parse(vFail?.content?.[0]?.text ?? '{}')
    ok('tampered validate: isError=true',             vFail?.isError === true)
    ok('tampered validate: status=SYSTEM_HALT',       vFailData.status === 'SYSTEM_HALT')
    ok('tampered validate: violations array',         Array.isArray(vFailData.violations))
    ok('tampered validate: violation key=spoke_count', vFailData.violations?.[0]?.key === 'spoke_count')
    ok('tampered validate: pass=false',               vFailData.pass === false)

    section('4c — TOOLS/CALL: vh2_ackermann')
    const ack = await request('tools/call', {
      name: 'vh2_ackermann',
      arguments: { steer_deg: 15 },
    })
    const ackData = JSON.parse(ack?.content?.[0]?.text ?? '{}')
    ok('ackermann call returns content',              !!ack?.content)
    ok('ackermann inner_deg present',                 typeof ackData.inner_deg === 'number')
    ok('ackermann outer_deg present',                 typeof ackData.outer_deg === 'number')
    ok('ackermann inner > outer (Ackermann law)',     ackData.inner_deg > ackData.outer_deg)
    ok('ackermann delta_deg > 0',                     ackData.delta_deg > 0)
    ok('ackermann turn_radius_m present',             typeof ackData.turn_radius_m === 'number')
    ok('ackermann isError absent',                    !ack?.isError)

    const ackNeg = await request('tools/call', {
      name: 'vh2_ackermann', arguments: { steer_deg: -20 },
    })
    const ackNegData = JSON.parse(ackNeg?.content?.[0]?.text ?? '{}')
    ok('ackermann negative steer: inner_deg < 0',     ackNegData.inner_deg < 0)
    ok('ackermann negative steer: |inner| > |outer|',
      Math.abs(ackNegData.inner_deg) > Math.abs(ackNegData.outer_deg))

    section('4d — TOOLS/CALL: vh2_kpi')
    const kpi = await request('tools/call', {
      name: 'vh2_kpi', arguments: {},
    })
    const kpiData = JSON.parse(kpi?.content?.[0]?.text ?? '{}')
    ok('kpi call returns content',                    !!kpi?.content)
    ok('kpi kpi_deg = 12.5 (default)',                kpiData.kpi_deg === 12.5)
    ok('kpi cos_kpi ≈ 0.97630',                       Math.abs(kpiData.cos_kpi - 0.97630) < 0.0001)
    ok('kpi sin_kpi ≈ 0.21644',                       Math.abs(kpiData.sin_kpi - 0.21644) < 0.0001)
    ok('kpi axis_unit_magnitude = 1',                 Math.abs(kpiData.axis_unit_magnitude - 1.0) < 0.000001)
    ok('kpi scrub_radius_mm = 45 (default)',          kpiData.scrub_radius_mm === 45)
    ok('kpi knuckle_local_x_m < 0 (FL side)',         kpiData.knuckle_local_x_m < 0)
    ok('kpi isError absent',                          !kpi?.isError)

    section('4e — TOOLS/CALL: vh2_witness (passthrough stub)')
    const wit = await request('tools/call', {
      name: 'vh2_witness',
      arguments: { any_field: 'accepted', another: 42 },  // arbitrary — passthrough
    })
    const witData = JSON.parse(wit?.content?.[0]?.text ?? '{}')
    ok('witness accepts arbitrary payload (passthrough)', !!wit?.content)
    ok('witness hex present',                         !!witData.hex)
    ok('witness hex length = 64',                     witData.hex?.length === 64)
    ok('witness tag present',                         !!witData.tag)
    ok('witness payload_keys includes any_field',     witData.payload_keys?.includes('any_field'))
    ok('witness isError absent',                      !wit?.isError)

    // Determinism check
    const wit2 = await request('tools/call', {
      name: 'vh2_witness',
      arguments: { any_field: 'accepted', another: 42 },
    })
    const wit2Data = JSON.parse(wit2?.content?.[0]?.text ?? '{}')
    ok('witness is deterministic (same payload → same hash)', witData.hex === wit2Data.hex)

    // Unknown tool
    section('4f — TOOLS/CALL: unknown tool error handling')
    const unknown = await request('tools/call', { name: 'no_such_tool', arguments: {} })
    ok('unknown tool returns isError=true',           unknown?.isError === true)
    ok('unknown tool returns error message',          !!unknown?.content?.[0]?.text)

    // ── [5] RESOURCE READS ──────────────────────────────────────────────
    section('5a — RESOURCES/READ: vh2://spec')
    const specRes = await request('resources/read', { uri: 'vh2://spec' })
    const specData = JSON.parse(specRes?.contents?.[0]?.text ?? '{}')
    ok('spec resource returns contents array',         Array.isArray(specRes?.contents))
    ok('spec resource uri = vh2://spec',              specRes?.contents?.[0]?.uri === 'vh2://spec')
    ok('spec resource mimeType = application/json',   specRes?.contents?.[0]?.mimeType === 'application/json')
    ok('spec.spoke_count = 5',                        specData.spoke_count === 5)
    ok('spec.kpi_deg = 12.5',                         specData.kpi_deg === 12.5)
    ok('spec.sovereignty = SAINTLY_HONESTY_TRUE',     specData.sovereignty === 'SAINTLY_HONESTY_TRUE')
    ok('spec._witness.tag present',                   !!specData._witness?.tag)
    ok('spec._constraints.count = 7',                 specData._constraints?.count === 7)

    section('5b — RESOURCES/READ: vh2://invariants')
    const invRes = await request('resources/read', { uri: 'vh2://invariants' })
    const invData = JSON.parse(invRes?.contents?.[0]?.text ?? '{}')
    ok('invariants resource returns contents',         Array.isArray(invRes?.contents))
    ok('invariants cos_kpi ≈ 0.97630',                Math.abs(invData.cos_kpi - 0.97630) < 0.0001)
    ok('invariants c5_spoke_angles_deg length = 5',   invData.c5_spoke_angles_deg?.length === 5)
    ok('invariants han_eigenvalue_mm = 0.82',         invData.han_eigenvalue_mm === 0.82)
    ok('invariants concavity_delta_pct ≈ 23.33',      Math.abs(invData.concavity_delta_pct - 23.33) < 0.01)

    section('5c — RESOURCES/READ: vh2://deploy')
    const depRes = await request('resources/read', { uri: 'vh2://deploy' })
    const depData = JSON.parse(depRes?.contents?.[0]?.text ?? '{}')
    ok('deploy resource returns contents',             Array.isArray(depRes?.contents))
    ok('deploy.docker.services.backend present',       !!depData.docker?.services?.backend)
    ok('deploy.kubernetes.namespace = vh2-prod',       depData.kubernetes?.namespace === 'vh2-prod')
    ok('deploy.argocd.app present',                   !!depData.argocd?.app)
    ok('deploy.mcp.tools length = 4',                 depData.mcp?.tools?.length === 4)
    ok('deploy.mcp.transport = StdioServerTransport', depData.mcp?.transport === 'StdioServerTransport')

    section('5d — RESOURCES/READ: unknown URI error')
    try {
      await request('resources/read', { uri: 'vh2://does-not-exist' })
      ok('unknown resource should have thrown', false)
    } catch (e) {
      ok('unknown resource throws JSON-RPC error',    !!e?.message)
    }

    // ── [6] KEEPALIVE ────────────────────────────────────────────────────
    section('6 — PING (keepalive)')
    const ping = await request('ping')
    ok('ping returns empty object',                   typeof ping === 'object')

    // ── [7] SCHEMA VALIDATION ────────────────────────────────────────────
    section('7 — SCHEMA VALIDATION (out-of-band)')
    // Import schema module directly to test the z.* API
    const { z } = await import('../src/schema.js')

    const schema = z.object({
      count: z.number().min(1).max(10),
      name:  z.string(),
      flag:  z.boolean().optional(),
    })
    const good = schema.safeParse({ count: 5, name: 'wheel' })
    ok('z.object safeParse valid input → success',    good.success)
    ok('z.object coerces number',                     good.data?.count === 5)

    const bad = schema.safeParse({ count: 0, name: 'wheel' })
    ok('z.object safeParse min violation → fail',     !bad.success)

    const pass_ = z.object({}).passthrough()
    const anyIn = pass_.safeParse({ x: 1, y: 'hello', z: true })
    ok('z.object({}).passthrough() accepts any input', anyIn.success)
    ok('passthrough preserves unknown keys',          anyIn.data?.x === 1 && anyIn.data?.y === 'hello')

    const js = z.object({ n: z.number(), s: z.string() }).toJsonSchema()
    ok('toJsonSchema returns type=object',            js.type === 'object')
    ok('toJsonSchema required=[n,s]',                 js.required?.includes('n') && js.required?.includes('s'))

  } finally {
    stop()
  }

  // ── SUMMARY ─────────────────────────────────────────────────────────────
  const elapsed = Date.now() - t0
  console.log(`\n${'─'.repeat(56)}`)
  console.log(`RESULT : ${pass} passed, ${fail} failed  (${elapsed}ms)`)

  if (fail > 0) {
    console.log('STATUS : ✗ SYSTEM HALT — MCP handshake verification failed')
    process.exit(1)
  }
  console.log('STATUS : ✓ SOVEREIGN PASS — MCP server fully verified')
  process.exit(0)
}

run().catch(err => {
  console.error('Fatal:', err)
  process.exit(1)
})

// ─────────────────────────────────────────────────────────────────────────────
// SSE TRANSPORT TESTS
// Spawns the server in SSE mode, opens a real HTTP connection, sends JSON-RPC
// via POST /message, reads responses from the SSE stream.
// ─────────────────────────────────────────────────────────────────────────────

import { request as httpRequest } from 'http'

async function runSseTests() {
  console.log('\n\n════ SSE TRANSPORT TESTS ════')

  let ssePass = 0, sseFail = 0
  const sseT0 = Date.now()

  const sse_ok  = (desc, val) => { if (val) { console.log(`  ✓ ${desc}`); ssePass++ } else { console.log(`  ✗ ${desc}`); sseFail++ } }

  // Spawn server in SSE mode
  const sseProc = spawn('node', [INDEX_JS], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: { ...process.env, MCP_TRANSPORT: 'sse', MCP_HTTP_PORT: '3099', MCP_HTTP_HOST: '127.0.0.1' },
  })
  sseProc.stderr.on('data', d => process.stderr.write(`  [sse-srv] ${d}`))

  // Wait for server to be listening
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('SSE server did not start in time')), 5000)
    sseProc.stderr.on('data', chunk => {
      if (chunk.toString().includes('listening')) { clearTimeout(timeout); setTimeout(resolve, 100) }
    })
  })

  section('8 — SSE /health')
  const health = await new Promise((res, rej) => {
    const r = httpRequest({ host:'127.0.0.1', port:3099, path:'/health', method:'GET' }, resp => {
      let body = ''
      resp.on('data', d => body += d)
      resp.on('end', () => res({ status: resp.statusCode, body: JSON.parse(body) }))
    })
    r.on('error', rej)
    r.end()
  })
  sse_ok('GET /health → 200',             health.status === 200)
  sse_ok('GET /health → ok:true',         health.body?.ok === true)
  sse_ok('GET /health → transport=sse',   health.body?.transport === 'sse')

  section('9 — SSE session establishment')
  // Open SSE stream, capture sessionId, then close
  const sessionId = await new Promise((resolve, reject) => {
    const r = httpRequest({
      host: '127.0.0.1', port: 3099, path: '/sse', method: 'GET',
      headers: { Accept: 'text/event-stream' },
    }, resp => {
      sse_ok('GET /sse → 200',                        resp.statusCode === 200)
      sse_ok('GET /sse → Content-Type: text/event-stream',
        resp.headers['content-type']?.startsWith('text/event-stream'))
      sse_ok('GET /sse → X-Session-Id header present', !!resp.headers['x-session-id'])

      let buf = ''
      resp.on('data', chunk => {
        buf += chunk.toString()
        // Parse first SSE event: event: session\ndata: {...}\n\n
        const match = buf.match(/event: session\ndata: ({.*?})\n\n/)
        if (match) {
          const data = JSON.parse(match[1])
          sse_ok('session event has sessionId',        !!data.sessionId)
          r.destroy()   // close the connection
          resolve(data.sessionId)
        }
      })
    })
    r.on('error', err => { if (err.code !== 'ECONNRESET') reject(err) })
    r.end()
  })

  section('10 — SSE POST /message round-trip')
  // Full round-trip: open SSE stream, post tools/list, read response
  const toolsResult = await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('SSE round-trip timeout')), 5000)

    // Open SSE stream
    let sid = null
    const sseReq = httpRequest({
      host: '127.0.0.1', port: 3099, path: '/sse', method: 'GET',
      headers: { Accept: 'text/event-stream' },
    }, resp => {
      let buf = ''
      resp.on('data', chunk => {
        buf += chunk.toString()

        // Extract sessionId from session event
        if (!sid) {
          const m = buf.match(/event: session\ndata: ({.*?})\n\n/)
          if (m) {
            sid = JSON.parse(m[1]).sessionId
            // POST tools/list once we have a session
            const body = JSON.stringify({ jsonrpc:'2.0', id:99, method:'tools/list', params:{} })
            const postReq = httpRequest({
              host:'127.0.0.1', port:3099,
              path:`/message?sessionId=${encodeURIComponent(sid)}`,
              method:'POST',
              headers:{ 'Content-Type':'application/json', 'Content-Length': Buffer.byteLength(body) },
            }, postResp => {
              sse_ok('POST /message → 202 Accepted', postResp.statusCode === 202)
            })
            postReq.end(body)
          }
        }

        // Extract data event (the JSON-RPC response)
        const dataMatch = buf.match(/\ndata: ({"jsonrpc".*?})\n\n/)
        if (dataMatch) {
          clearTimeout(timeout)
          sseReq.destroy()
          resolve(JSON.parse(dataMatch[1]))
        }
      })
    })
    sseReq.on('error', err => { if (err.code !== 'ECONNRESET') reject(err) })
    sseReq.end()
  })

  sse_ok('SSE response has jsonrpc=2.0',        toolsResult?.jsonrpc === '2.0')
  sse_ok('SSE response id=99',                  toolsResult?.id === 99)
  sse_ok('SSE tools/list result has tools array', Array.isArray(toolsResult?.result?.tools))
  sse_ok('SSE tools/list returns 4 tools',       toolsResult?.result?.tools?.length === 4)

  section('11 — SSE 404 for unknown path')
  const notFound = await new Promise((res, rej) => {
    const r = httpRequest({ host:'127.0.0.1', port:3099, path:'/no-such-path', method:'GET' }, resp => {
      res(resp.statusCode)
    })
    r.on('error', rej)
    r.end()
  })
  sse_ok('Unknown path → 404',    notFound === 404)

  section('12 — SSE POST /message without sessionId → 400')
  const noSession = await new Promise((res, rej) => {
    const body = JSON.stringify({ jsonrpc:'2.0', id:1, method:'ping', params:{} })
    const r = httpRequest({
      host:'127.0.0.1', port:3099, path:'/message', method:'POST',
      headers:{ 'Content-Type':'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, resp => { res(resp.statusCode) })
    r.on('error', rej)
    r.end(body)
  })
  sse_ok('POST /message without sessionId → 400', noSession === 400)

  sseProc.kill()

  const sseElapsed = Date.now() - sseT0
  console.log(`\n${'─'.repeat(56)}`)
  console.log(`SSE RESULT : ${ssePass} passed, ${sseFail} failed  (${sseElapsed}ms)`)
  return { ssePass, sseFail }
}

runSseTests().then(({ ssePass, sseFail }) => {
  if (sseFail > 0) {
    console.log('SSE STATUS : ✗ SYSTEM HALT — SSE transport tests failed')
    process.exit(1)
  }
  console.log('SSE STATUS : ✓ SOVEREIGN PASS — SSE transport verified')
}).catch(err => {
  console.error('SSE Fatal:', err)
  process.exit(1)
})
