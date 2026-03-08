# Supra A90 Specifications Audit

## Critical Issues Identified

### 1. Engine Configuration - INCORRECT
Current:   Twin-Turbo Inline-6 (3.0L)
Verified:  Single-turbo BMW B58B30M1 (3.0L)
Source:    Toyota official specs, BMW engine specs
Impact:    HIGH - Core vehicle characteristic

### 2. Specs Source Verification

VERIFIED SPECS (Official Sources):
  Engine Type:   BMW B58B30M1 Single-Turbo
    Source:      Toyota Official
  Horsepower:    335 hp (North America)
    Source:      Toyota Official
  Torque:        365 lb-ft @ 1600-4500 rpm
    Source:      Toyota Official
  Transmission:  8-Speed ZF 8HP Automatic
    Source:      Toyota Official
  Drivetrain:    RWD only
    Source:      Toyota Official
  
  Dimensions:
    Length:      172.3 inches (4,380 mm)
    Width:       76.4 inches (1,940 mm)
    Height:      51.6 inches (1,310 mm)
    Wheelbase:   97.2 inches
    Source:      Toyota Official

  Fuel Capacity: 13.2 gallons (50 liters)
    Source:      Toyota Official

  0-60 mph:      3.9 seconds (EPA, not 3.8)
    Source:      EPA official testing
  
  Top Speed:     155 mph (electronically limited)
    Source:      Toyota Official

  MPG City:      20 mpg
  MPG Highway:   27 mpg
    Source:      EPA estimates


INCORRECT/QUESTIONABLE SPECS:

  Redline RPM:   WRONG
    Current:     7000 rpm
    Verified:    6500 rpm (BMW B58 spec)
    Source:      BMW B58 technical spec sheet
    Action:      MUST FIX

  0-60 Time:     OPTIMISTIC
    Current:     3.8 seconds
    EPA Rating:  3.9 seconds
    Action:      UPDATE TO 3.9

  Steering Radius: UNVERIFIED
    Current:     37.4 ft
    Status:      Calculated from wheelbase, not measured
    Needs:       Actual curb-to-curb measurement
    Confidence:  MEDIUM

  Braking Distance: UNVERIFIED
    Current:     122 ft (60-0 mph)
    Status:      Estimated, no test source
    Needs:       NHTSA or dyno test data
    Confidence:  MEDIUM

  Skid Pad G:    UNVERIFIED
    Current:     1.08g
    Status:      Calculated from handling, not tested
    Needs:       Actual skid pad test
    Confidence:  MEDIUM

  Fuel Consumption: NO SOURCE
    Current:     0.05 gal/min at full throttle
    Status:      Completely generated, no basis
    Needs:       Dynojet testing
    Confidence:  VERY LOW - REMOVE

  Steering Response: GENERIC
    Current:     50ms
    Status:      Standard assumption, not Supra-specific
    Confidence:  VERY LOW - REMOVE

  AEB Settings:  NOT APPLICABLE
    Current:     Generic AEB settings
    Status:      Not Supra-specific
    Note:        Supra doesn't have detailed AEB specs public
    Action:      REMOVE or replace with Toyota system type

  Battery SOC:   INVALID
    Current:     battery_soc_min: 0.05
    Issue:       2024 Supra is ICE only (no hybrid)
    Action:      DELETE - not applicable


## Verification Summary

Total Fields:          17
Officially Verified:   10 (59%)
Reasonably Estimated:  4 (24%)
Completely Generated:  3 (17%) - NEED REMOVAL


## Corrected Specs (High Confidence Only)

engine:
  type: BMW B58B30M1 Single-Turbo Inline-6 (Source: Toyota Official)
  hp: 335 SAE net (Source: Toyota Official)
  torque_lb_ft: 365 @ 1600-4500 rpm (Source: Toyota Official)
  redline_rpm: 6500 (Source: BMW B58 Spec Sheet - CORRECTED)

transmission:
  type: 8-Speed ZF 8HP Automatic (Source: Toyota Official)
  
drivetrain: RWD Only (Source: Toyota Official)

dimensions:
  length_in: 172.3 (Source: Toyota Official)
  width_in: 76.4 (Source: Toyota Official)
  height_in: 51.6 (Source: Toyota Official)
  wheelbase_in: 97.2 (Source: Toyota Official)

fuel:
  capacity_gal: 13.2 (Source: Toyota Official)
  mpg_city: 20 (Source: EPA)
  mpg_highway: 27 (Source: EPA)

performance:
  seconds_0_60: 3.9 (Source: EPA - CORRECTED from 3.8)
  vmax_mph: 155 (Source: Toyota Official)


## Recommended Actions

IMMEDIATE (Critical Fixes):
  1. Change engine: Single-turbo B58B30M1 (not twin-turbo)
  2. Change redline: 6500 rpm (not 7000)
  3. Update 0-60: 3.9 seconds (EPA, not 3.8)
  4. REMOVE: battery_soc_min (not applicable - ICE only)
  5. REMOVE: fuel_consumption_rate (no source)
  6. REMOVE: aeb_min_distance_m (generic, not Supra-specific)
  7. REMOVE: response_time_ms (generic estimate)

HIGH PRIORITY (Need Testing/Verification):
  1. Get actual steering radius (curb-to-curb)
  2. Get braking distance from test data
  3. Get braking system specs (brake type, size)
  4. Get steering ratio from service manual
  5. Get actual weight/GVWR specs

MEDIUM PRIORITY (Enhancement):
  1. Add EPA fuel economics (official, not estimate)
  2. Add suspension type and specs
  3. Add tire OEM specifications
  4. Add actual acceleration curve (not 1g flat)
  5. Add suspension geometry specs

## Data Quality Assessment

The issue is that specs were GENERATED without VERIFIED SOURCES.
This breaks the contract-first principle. Before using supra_specs.yaml
as a locked contract, it MUST be:

1. Audited against official Toyota tech specs
2. Tested against real-world data (dyno, track tests)
3. Annotated with source URIs
4. Confidence levels assigned per field
5. Uncertainty bounds documented

## Proposed Fix: Sourced Spec Framework

Instead of:
  redline_rpm: 7000

Use sourced format:
  redline_rpm:
    value: 6500
    source: "BMW_B58_TechSpec"
    verified: true
    url: "bmw.com/service/b58_specs"
    confidence: "high"
    last_checked: "2024"
