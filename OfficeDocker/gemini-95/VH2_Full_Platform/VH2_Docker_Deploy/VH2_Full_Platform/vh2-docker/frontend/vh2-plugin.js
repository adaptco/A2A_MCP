/**
 * VH2 SOVEREIGN SUSPENSION PLUGIN
 * Web Component — drop-in embeddable for any website
 *
 * Usage:
 *   <script src="/vh2-plugin.js"></script>
 *   <vh2-simulator></vh2-simulator>
 *
 * Attributes:
 *   api-base   — backend API base URL (default: /api)
 *   height     — iframe height (default: 100%)
 *   mode       — "sim" | "test" | "split" (default: "sim")
 *   theme      — "dark" | "light" (default: "dark")
 */

;(function () {
  'use strict'

  // Guard against double-registration
  if (customElements.get('vh2-simulator')) return

  const PLUGIN_VERSION = '1.0.0'
  const DEFAULT_API    = '/api'

  // ── INLINE STYLES (Shadow DOM — zero bleed) ───────────────────────────────
  const CSS = `
    :host {
      display: block;
      width: 100%;
      height: var(--vh2-height, 600px);
      min-height: 320px;
      background: #05050c;
      border: 1px solid rgba(212,175,55,.22);
      box-sizing: border-box;
      position: relative;
      font-family: 'Share Tech Mono', monospace;
      contain: content;
    }
    /* Mobile-first: full viewport on small screens */
    @media (max-width: 768px) {
      :host { height: var(--vh2-height, 100svh); border: none; }
    }
    #shell {
      width: 100%; height: 100%;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    #toolbar {
      background: rgba(5,5,18,.96);
      border-bottom: 1px solid rgba(212,175,55,.18);
      display: flex; align-items: center; gap: 10px;
      padding: 7px 14px; flex-wrap: wrap;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }
    .brand {
      font-size: 8px; letter-spacing: 3px;
      color: #D4AF37; white-space: nowrap; margin-right: 6px;
    }
    .pill {
      font-size: 7px; letter-spacing: 1px; padding: 3px 9px;
      border: 1px solid rgba(212,175,55,.3); color: #D4AF37;
      background: rgba(212,175,55,.06); cursor: pointer;
      transition: background .15s; white-space: nowrap;
      border-radius: 1px; user-select: none;
    }
    .pill:hover, .pill.on { background: rgba(212,175,55,.22); border-color: #D4AF37; }
    .pill.ok  { border-color: #3dbd72; color: #3dbd72; background: rgba(61,189,114,.06); }
    .pill.err { border-color: #c04040; color: #c04040; }
    .spacer { flex: 1; }
    .status { font-size: 7px; color: #30304a; letter-spacing: 1px; }
    #frames {
      width: 100%; height: 100%;
      display: grid; overflow: hidden;
    }
    #frames.split { grid-template-columns: 1fr 1fr; }
    @media (max-width: 600px) {
      #frames.split { grid-template-columns: 1fr; grid-template-rows: 1fr 1fr; }
    }
    iframe {
      width: 100%; height: 100%;
      border: none; display: block;
      /* Mobile native: allow hardware-accelerated scroll in iframe */
      -webkit-overflow-scrolling: touch;
    }
    #frames.split iframe:first-child {
      border-right: 1px solid rgba(212,175,55,.12);
    }
    @media (max-width:600px) {
      #frames.split iframe:first-child { border-right:none; border-bottom:1px solid rgba(212,175,55,.12); }
    }
    /* Validation overlay */
    #vbadge {
      position: absolute; bottom: 12px; right: 12px;
      font-size: 7px; letter-spacing: 1.5px; padding: 4px 10px;
      border: 1px solid; pointer-events: none;
      opacity: 0; transition: opacity .4s;
    }
    #vbadge.show { opacity: 1; }
    #vbadge.pass { border-color: #3dbd72; color: #3dbd72; background: rgba(61,189,114,.1); }
    #vbadge.fail { border-color: #c04040; color: #c04040; background: rgba(192,64,64,.1); }
    /* Loading skeleton */
    #loader {
      position: absolute; inset: 0;
      background: #05050c; display: flex;
      flex-direction: column; align-items: center; justify-content: center;
      gap: 12px; transition: opacity .5s;
    }
    #loader.gone { opacity: 0; pointer-events: none; }
    .spin {
      width: 32px; height: 32px;
      border: 2px solid rgba(212,175,55,.15);
      border-top-color: #D4AF37;
      border-radius: 50%;
      animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .load-text { font-size: 7px; letter-spacing: 2px; color: rgba(212,175,55,.4); }
  `

  // ── WEB COMPONENT ─────────────────────────────────────────────────────────
  class VH2Simulator extends HTMLElement {
    static get observedAttributes() { return ['mode', 'api-base', 'height', 'theme'] }

    constructor() {
      super()
      this._root = this.attachShadow({ mode: 'open' })
      this._apiBase = DEFAULT_API
      this._mode = 'sim'
      this._validated = false
    }

    connectedCallback() {
      this._apiBase = this.getAttribute('api-base') || DEFAULT_API
      this._mode    = this.getAttribute('mode')     || 'sim'
      const height  = this.getAttribute('height')   || null
      if (height) this.style.setProperty('--vh2-height', height)
      this._render()
      this._loadIframes()
      this._validate()
    }

    attributeChangedCallback(name, _old, val) {
      if (!this._root.innerHTML) return
      if (name === 'mode') { this._mode = val; this._applyMode() }
    }

    _render() {
      const style = document.createElement('style')
      style.textContent = CSS
      this._root.appendChild(style)

      this._root.innerHTML += `
        <div id="shell">
          <div id="toolbar">
            <span class="brand">VH2 · ADVAN GT BEYOND C5</span>
            <button class="pill on"  id="btn-sim"   title="3D Vehicle Simulation">SIM</button>
            <button class="pill"     id="btn-test"  title="Unit Test Runner">TESTS</button>
            <button class="pill"     id="btn-split" title="Split View">SPLIT</button>
            <span class="spacer"></span>
            <span class="status" id="api-status">API: connecting…</span>
            <span class="status" id="ver-tag">v${PLUGIN_VERSION}</span>
          </div>
          <div id="frames">
            <iframe id="f-sim"  src="/vehicle.html"  title="VH2 Vehicle Simulation"
                    allow="accelerometer; fullscreen" loading="lazy"></iframe>
            <iframe id="f-test" src="/tests.html"    title="VH2 Unit Tests"
                    style="display:none"              loading="lazy"></iframe>
          </div>
        </div>
        <div id="loader">
          <div class="spin"></div>
          <div class="load-text">INITIALISING VH2 RIG…</div>
        </div>
        <div id="vbadge"></div>
      `

      // Button bindings
      this._root.getElementById('btn-sim').addEventListener('click',   () => this._setMode('sim'))
      this._root.getElementById('btn-test').addEventListener('click',  () => this._setMode('test'))
      this._root.getElementById('btn-split').addEventListener('click', () => this._setMode('split'))

      // Hide loader once first iframe loads
      const simFrame = this._root.getElementById('f-sim')
      simFrame.addEventListener('load', () => {
        setTimeout(() => this._root.getElementById('loader').classList.add('gone'), 400)
      }, { once: true })
    }

    _setMode(mode) {
      this._mode = mode
      this._applyMode()
      ;['btn-sim','btn-test','btn-split'].forEach(id => {
        this._root.getElementById(id).classList.toggle('on', id === `btn-${mode}`)
      })
    }

    _applyMode() {
      const frames  = this._root.getElementById('frames')
      const fSim    = this._root.getElementById('f-sim')
      const fTest   = this._root.getElementById('f-test')
      frames.className = this._mode === 'split' ? 'split' : ''
      fSim.style.display  = this._mode === 'test'  ? 'none' : ''
      fTest.style.display = this._mode === 'sim'   ? 'none' : ''
    }

    async _validate() {
      const badge  = this._root.getElementById('vbadge')
      const status = this._root.getElementById('api-status')
      try {
        const res  = await fetch(`${this._apiBase}/validate`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            spoke_count:5, rim_diameter_in:19, front_et_mm:29,
            rear_et_mm:22, kpi_deg:12.5, scrub_radius_mm:45, c5_sector_deg:72,
          }),
        })
        const data = await res.json()
        this._validated = data.pass
        status.textContent = `API: ${data.status}`
        status.style.color = data.pass ? '#3dbd72' : '#c04040'
        badge.textContent  = data.pass
          ? `✓ ${data.witness?.tag || 'SOVEREIGN PASS'}`
          : `✗ SYSTEM HALT · ${data.violations?.[0]?.key}`
        badge.className    = `${data.pass ? 'pass' : 'fail'} show`
        this.dispatchEvent(new CustomEvent('vh2:validated', {
          detail: data, bubbles: true, composed: true,
        }))
      } catch (_) {
        status.textContent = 'API: offline'
        badge.textContent  = '⚠ BACKEND OFFLINE'
        badge.className    = 'err show'
        this.dispatchEvent(new CustomEvent('vh2:offline', { bubbles: true, composed: true }))
      }
      setTimeout(() => badge.classList.remove('show'), 5000)
    }

    _loadIframes() {
      // Lazy-load test frame only when needed
      const fTest = this._root.getElementById('f-test')
      this._root.getElementById('btn-test').addEventListener('click', () => {
        if (!fTest.src.includes('tests')) fTest.src = '/tests.html'
      }, { once: true })
    }

    // Public API
    validate() { return this._validate() }
    setMode(m)  { this._setMode(m) }
    get isValidated() { return this._validated }
  }

  customElements.define('vh2-simulator', VH2Simulator)

  // ── AUTO-UPGRADE any existing <vh2-simulator> tags ────────────────────────
  console.log(`[VH2 Plugin v${PLUGIN_VERSION}] Web component registered`)
})()
