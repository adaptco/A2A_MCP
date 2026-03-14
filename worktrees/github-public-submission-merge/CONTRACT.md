# Supra Domain Contract v1.0.0

> **THIS IS A BINDING SPECIFICATION DOCUMENT**
>
> All avatars, agents, judges, simulators, and frontend code **MUST** respect these specifications.
> Changes require explicit version bump and notification to dependent systems.

---

## 1. Vehicle Specification: Toyota GR Supra A90 (2024 GT500)

### Engine & Powertrain

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Engine** | Twin-Turbo Inline-6 (3.0L) | BMW-derived B58 platform |
| **Horsepower** | 335 hp @ 5000-6500 RPM | |
| **Torque** | 365 lb-ft | Peak across mid-range |
| **Redline** | 7000 RPM | Hard limit |
| **Idle** | 650 RPM | |
| **Transmission** | 8-Speed Automatic | ZF 8HP45 |
| **Drivetrain** | RWD (Rear-Wheel Drive) | No AWD in current spec |

### Performance Envelope

| Metric | Value | Notes |
|--------|-------|-------|
| **0-60 mph** | 3.8s | Hardcoded contract time |
| **0-100 mph** | 9.1s | Must respect this curve |
| **60-100 mph** | 4.8s | Gear-dependent |
| **Top Speed** | 155 mph | Electronic limiter (vmax_kmh: 249) |
| **Braking (60→0)** | 122 ft | Must not exceed this |
| **Lateral Grip** | 1.08g | Skid pad (ESC threshold) |
| **Max Lat Accel** | 1.1g | Handling limit |
| **Max Decel** | 1.2g | Braking limit |

### Dimensions & Weight

| Dimension | Value | Notes |
|-----------|-------|-------|
| **Length** | 172.3 in (4.38 m) | Collision box |
| **Width** | 76.4 in (1.94 m) | Collision box |
| **Height** | 51.6 in (1.31 m) | Collision box |
| **Wheelbase** | 97.2 in | Affects turning |
| **Weight** | 3397 lbs (1540 kg) | Affects acceleration |
| **Ground Clearance** | 4.8 in | Affects off-road |

### Handling Characteristics

| Characteristic | Value | Notes |
|---------------|-------|-------|
| **Turning Radius** | 37.4 ft | Hard constraint |
| **Steering Ratio** | 12:1 | Sensitivity |
| **Steering Response** | ~50 ms | Input latency |
| **Balance** | Neutral | Neither front nor rear-heavy bias |
| **Ride Height** | Stock | No suspension mods |
| **Approach Angle** | 13.0° | Front scrape threshold |
| **Departure Angle** | 20.0° | Rear scrape threshold |

### Fuel & Efficiency

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Tank Capacity** | 13.2 gallons | Full tank range: ~355 miles |
| **City MPG** | 20 | Steady-state city driving |
| **Highway MPG** | 27 | Steady-state highway (55 mph) |
| **Consumption Rate** | 0.05 gal/min | At full throttle |
| **Fuel Pressure** | 50 psi | Fuel system nominal |

### Constraints & Limits

**Hard Limits (non-negotiable):**
- Maximum speed: **155 mph** (vmax_mph)
- Maximum lateral g: **1.08g** (ESC engagement point)
- Minimum turning radius: **37.4 ft** (steering geometry)
- Turning radius cap: **25 ft minimum** (physical limit)
- Braking distance cap: **122 ft** (60→0 target)

**Soft Limits (warnings, not failures):**
- Fuel <10%: low-fuel warning (still operable)
- tire wear >90%: performance degradation
- Engine temp >110°C: warning (still operable)

---

## 2. Judge Criteria Scoring Rubric

### Criteria Hierarchy

```
Overall Action Score
├── SAFETY (weight: 1.0) ★★★ CRITICAL
│   ├── bounds_check: stay in Base44 cell
│   ├── collision_avoidance: min distance 2m
│   ├── overspeed_check: respect vmax + zone limits
│   ├── fuel_viability: have fuel to execute
│   └── stability_margin: lateral g < ESC threshold
│
├── SPEC_ALIGNMENT (weight: 0.8) ★★ STRONG
│   ├── acceleration_realism: 0-60 envelope
│   ├── handling_compliance: turning radius
│   ├── braking_fidelity: stopping distance
│   └── engine_response: realistic spool-up
│
├── PLAYER_INTENT (weight: 0.7) ★★ MODERATE
│   ├── objective_progress: advancing goal
│   ├── tactical_fit: context match
│   └── style_match: avatar personality
│
└── LATENCY (weight: 0.5) ★ LIGHT
    ├── execution_time: <16.67ms @ 60 FPS
    └── response_quality: full compute, not skipped
```

### Safety Sub-Criteria Scoring

**Bounds Check:**
```
in_bounds:          1.0
warning_zone (90%): 0.7
out_of_bounds:      0.0
```

**Collision Avoidance:**
```
clear_safe (>5m):     1.0
approaching (2-5m):   0.6
collision (<0.5m):    0.0
```

**Overspeed:**
```
speed ≤ 95% vmax: 1.0
speed ≤ 100% vmax: 0.7
speed > vmax: 0.0
```

**Fuel Viability:**
```
fuel > 20%: 1.0
fuel 10-20%: 0.8
fuel < 10%: 0.3
no fuel: 0.0
```

**Stability Margin (lateral g):**
```
lateral_g ≤ 0.8 × ESC: 1.0
lateral_g ≤ 1.0 × ESC: 0.8
lateral_g > 1.0 × ESC: 0.0
```

### Spec Alignment Sub-Criteria Scoring

**Acceleration Realism:**
```
within 0-60 envelope (≤3.8s): 1.0
slightly slow (3.8-4.5s): 0.8
well below spec (>4.5s): 0.4
```

**Handling Compliance:**
```
turning radius ≤ 37.4 ft: 1.0
slight deviation: 0.85
significant deviation: 0.4
```

**Braking Fidelity:**
```
60→0 distance ≤ 122 ft: 1.0
slightly longer: 0.85
well longer: 0.4
```

### Player Intent Sub-Criteria Scoring

**Objective Progress:**
```
direct progress: 1.0
indirect contribution: 0.85
neutral impact: 0.5
regressive: 0.0
```

**Style Match (per Avatar):**
- **Engineer**: Conservative actions (0.95 of vmax) → score 1.0; aggressive (>1.0 × vmax) → score 0.2
- **Designer**: Creative paths → 1.0; mundane routes → 0.4
- **Driver**: Fun, engaging actions → 1.0; boring safe paths → 0.4

### Latency Sub-Criteria Scoring

**Execution Time (16.67ms budget @ 60 FPS):**
```
elapsed ≤ 12.5ms (75% budget): 1.0
elapsed ≤ 16.67ms (100% budget): 0.9
elapsed ≤ 25ms (150% budget): 0.5
elapsed > 25ms (timeout): 0.0
```

### Overall Score Calculation

```
overall_score = Σ(criterion.weight × criterion.score) / Σ(criterion.weight)

Interpretation:
0.9-1.0: EXCELLENT (all green)
0.7-0.9: GOOD (mostly compliant)
0.5-0.7: ACCEPTABLE (mixed)
0.0-0.5: POOR (failures)
```

### Tuning Presets

#### Preset: `simulation` (Default)
```yaml
safety_weight: 1.0
spec_alignment_weight: 1.0
player_intent_weight: 0.5
latency_weight: 1.0
description: "Realistic, challenging, spec-strict"
```

#### Preset: `arcade`
```yaml
safety_weight: 0.5
spec_alignment_weight: 0.4
player_intent_weight: 1.0
latency_weight: 0.3
description: "Fast, fun, forgiving"
```

#### Preset: `casual`
```yaml
safety_weight: 0.9
spec_alignment_weight: 0.6
player_intent_weight: 0.9
latency_weight: 0.2
description: "Balanced for fun"
```

---

## 3. Binding Constraints for Dependent Systems

### For Avatars

- **must** respect overspeed constraints (judge will penalize)
- **must** understand Supra limits (top speed, turning radius, acceleration curve)
- **may** have personality modifiers (conservative engineer, aggressive driver) but not violate specs

### For Agents

- **must** consult Judge before commanded actions
- **must** query World Vectors for Supra specs when unsure
- **may** cache specs locally but invalidate on version change
- **must** include context (speed, fuel, position, objective) when requesting judge score

### For WHAM Engine

- **must** enforce hard limits (155 mph, 37.4 ft radius, 1.08g lateral)
- **must** enforce physics bounds (no motion above vmax without explicit override)
- **must** simulate fuel consumption at 0.05 gal/min when throttle > 0
- **must** generate telemetry for judge evaluation

### For WebGL Frontend

- **must** display telemetry (speed, rpm, fuel, temperature) per Supra's gauge definitions
- **must** never allow UI to override hard constraints
- **may** render visual warnings (fuel low, temp high, overspeed) without blocking action

### For World Vectors

- **must** index all Supra specs from `specs/supra_specs.yaml`
- **must** make specs searchable via semantic similarity
- **must** tag entries with source version (v1.0.0)

### For Judge

- **must** load criteria weights from `specs/judge_criteria.yaml`
- **must** respect preset selection (simulation, arcade, casual)
- **must** implement scoring functions exactly as defined

---

## 4. Version Control & Change Protocol

**Current Version**: `1.0.0`

**Change Procedure:**

1. Update `specs/supra_specs.yaml` or `specs/judge_criteria.yaml`
2. Bump version in file header
3. Create git commit with tag: `spec-v1.0.X`
4. Notify dependent systems (agents, avatars, frontend, judge)
5. Dependent systems must validate against new spec within 2 commits

**Example:**
```bash
git tag spec-v1.0.1 -m "Bump tire wear rate from 0.01 to 0.02%/hour"
git push origin spec-v1.0.1
```

---

## 5. Test Contract Validation

All systems **must** pass:

```python
def test_supra_contract():
    # Load contract specs
    loader = get_loader()
    supra = loader.load_supra_specs()

    # Assert critical limits
    assert supra["performance"]["vmax_mph"] == 155, "vmax must be 155 mph"
    assert supra["performance"]["acceleration"]["seconds_0_60"] == 3.8, "0-60 must be 3.8s"
    assert supra["handling_characteristics"]["braking_distance_60_ft"] == 122, "braking must be 122 ft"
    assert supra["handling_characteristics"]["skid_pad_g"] == 1.08, "ESC threshold 1.08g"
    assert supra["handling_characteristics"]["steering"]["turning_radius_ft"] == 37.4, "turning radius 37.4 ft"

def test_judge_contract():
    # Load judge specs
    judge = JudgmentModel(preset="simulation")

    # Assert criteria are loaded
    assert len(judge._criteria) == 4, "Must have 4 criteria"
    assert judge._criteria[CriteriaType.SAFETY].weight == 1.0, "Safety weight 1.0"
    assert judge._criteria[CriteriaType.SPEC_ALIGNMENT].weight == 0.8, "Spec weight 0.8"
```

---

## 6. Glossary

| Term | Definition |
|------|-----------|
| **vmax** | Vehicle maximum speed (155 mph) |
| **ESC** | Electronic Stability Control threshold (1.08g lateral) |
| **MCDA** | Multi-Criteria Decision Analysis (judge framework) |
| **Base44** | Logical game world grid (4×4×3 zones) |
| **Spec Alignment** | adherence to Supra physics specs |
| **Telemetry** | Real-time vehicle state (speed, rpm, fuel, temp, g-forces) |
| **Preset** | Judge tuning mode (simulation, arcade, casual) |

---

**Contract Effective**: 2026-02-12
**Next Review**: 2026-03-12
**Status**: LOCKED ✅
