# VH2 · Sovereign Suspension Rig — Docker Deploy

**Advan GT Beyond C5 · 5-spoke · KPI 12.5° · Ackermann Steering · SHA-256 Witnessed**

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     BROWSER / MOBILE                │
└────────────────────────┬────────────────────────────┘
                         │ :80
              ┌──────────▼──────────┐
              │    NGINX PROXY      │  (vh2-public network)
              │  reverse proxy +    │
              │  gzip + cache hdrs  │
              └─────┬─────────┬─────┘
                    │         │         (vh2-internal network)
         /api/*     │         │  /*
     ┌──────────────▼─┐   ┌───▼──────────────────┐
     │ BACKEND SOCKET  │   │  FRONTEND SOCKET     │
     │  Express :3001  │   │   Express :3000      │
     │                 │   │                      │
     │  POST /validate │   │  GET /               │
     │  GET  /spec     │   │  GET /vehicle.html   │  ← VH2 Sim artifact
     │  GET  /kpi      │   │  GET /tests.html     │  ← Unit test artifact
     │  GET  /ackermann│   │  GET /vh2-plugin.js  │  ← Web Component
     │  GET  /health   │   │                      │
     └─────────────────┘   └──────────────────────┘
```

## Quick Start

```bash
# Clone / unzip this folder, then:
chmod +x scripts/deploy.sh

# Full pipeline (test → build → deploy → validate)
./scripts/deploy.sh

# Then open:
#   http://localhost              ← plugin demo
#   http://localhost/vehicle.html ← raw simulation
#   http://localhost/tests.html   ← unit test runner
#   http://localhost/api/spec     ← canonical spec + witness hash
```

## Commands

| Command | Action |
|---|---|
| `./scripts/deploy.sh` | Full pipeline: test → build → up → validate |
| `./scripts/deploy.sh test` | Server-side unit tests only (fail-closed) |
| `./scripts/deploy.sh build` | Build Docker images |
| `./scripts/deploy.sh up` | Start stack |
| `./scripts/deploy.sh down` | Stop stack |
| `./scripts/deploy.sh validate` | Hit live API with canonical spec |
| `./scripts/deploy.sh logs` | Tail all service logs |
| `./scripts/deploy.sh status` | Show health + endpoints |
| `./scripts/deploy.sh clean` | Remove all containers + images |

## Plugin Embed

Drop into **any website** with two lines:

```html
<script src="https://yourdomain.com/vh2-plugin.js" defer></script>
<vh2-simulator mode="sim" api-base="https://yourdomain.com/api" height="600px"></vh2-simulator>
```

### Attributes

| Attribute | Values | Default |
|---|---|---|
| `mode` | `sim` \| `test` \| `split` | `sim` |
| `api-base` | URL to backend API | `/api` |
| `height` | Any CSS height | `600px` (auto on mobile) |

### Events

```js
document.querySelector('vh2-simulator').addEventListener('vh2:validated', e => {
  console.log(e.detail.witness.tag)   // 0xVH2_ET29_ET22_C5_SOV_XXXXXX
  console.log(e.detail.pass)          // true | false
})
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/spec` | Canonical spec + witness hash |
| `POST` | `/api/validate` | Fail-closed constraint validator |
| `POST` | `/api/witness` | SHA-256 hash any object |
| `GET` | `/api/ackermann/:deg` | Ackermann angles at steer angle |
| `GET` | `/api/kpi` | KPI kinematics constants |

### Validate Example

```bash
curl -X POST http://localhost/api/validate \
  -H 'Content-Type: application/json' \
  -d '{"spoke_count":5,"rim_diameter_in":19,"front_et_mm":29,
       "rear_et_mm":22,"kpi_deg":12.5,"scrub_radius_mm":45,"c5_sector_deg":72}'

# → {"pass":true,"status":"SOVEREIGN_PASS","witness":{"tag":"0xVH2_ET29_ET22_C5_SOV_..."}}
# Tampered field → {"pass":false,"status":"SYSTEM_HALT","violations":[...]}
```

## Physical Invariants

| Constraint | Value |
|---|---|
| Spoke count | 5 (C5 symmetry, 72° pitch) |
| Rim diameter | 19" |
| Front offset | ET+29mm · concavity 0.150 |
| Rear offset | ET+22mm · concavity 0.185 |
| KPI angle | 12.5° |
| Scrub radius | 45mm (positive) |
| Han eigenvalue | 0.82mm |
| Hausdorff limit | < 0.20mm |
| Ising universality | 0.9982 |

## Production Deploy

```bash
ALLOWED_ORIGIN=https://yourdomain.com \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

*SHA-256 Witnessed · Saintly Honesty Enforced · Three.js r128 · Node 20 LTS*
