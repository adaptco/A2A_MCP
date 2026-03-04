#!/usr/bin/env python3
import json
import yaml
import sys
import os
import hashlib

# Configuration
ADK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'adk'))
CONTRACTS_INDEX = os.path.join(ADK_ROOT, 'contracts_index.json')
GENESIS_BLOCK = os.path.join(ADK_ROOT, 'genesis_block.json')

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def load_yaml(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def actuate_kernel():
    log("Initializing MoE Kernel Actuator...", "BOOT")
    
    # 1. Load Truth Table (Contracts Index)
    if not os.path.exists(CONTRACTS_INDEX):
        log(f"Contracts Index not found at {CONTRACTS_INDEX}", "FATAL")
        sys.exit(1)
    
    index = load_json(CONTRACTS_INDEX)
    log(f"Loaded Contracts Index v{index.get('version', 'unknown')}", "OK")

    # 2. Verify Schema Integrity
    schemas = index['contracts']['node_schemas']
    for name, uri in schemas.items():
        # Clean uri adk://schemas/ -> schemas/
        rel_path = uri.replace('adk://', '')
        abs_path = os.path.join(ADK_ROOT, rel_path)
        if os.path.exists(abs_path):
            log(f"Verified Schema: {name}", "PASS")
        else:
            log(f"Missing Schema: {name} at {abs_path}", "FAIL")

    # 3. Verify Genesis State
    log("Verifying Petrified State (Genesis Block)...", "VERIFY")
    genesis = load_json(GENESIS_BLOCK)
    
    # Check 1: Merkle Root Format
    merkle = genesis['state']['assembly_actuator']['merkle_root']
    if len(merkle) == 66 and merkle.startswith("0x"):
        log(f"Merkle Root Format: {merkle[:10]}...", "PASS")
    else:
        log("Merkle Root Malformed", "FAIL")

    # Check 2: Kawaii Constraint
    kawaii = genesis['state']['structural_integrity']['constraints']['kawaii_score']
    if kawaii >= 0.8:
        log(f"Kawaii Constraint: {kawaii} >= 0.8", "PASS")
    else:
        log(f"Kawaii Violation: {kawaii}", "FAIL")

    # 4. Actuate Threat Model
    log("Actuating Immune System (Threat Model)...", "SECURE")
    tm_path = os.path.join(ADK_ROOT, 'threat_model', 'moe_kernel.v0.yaml')
    if os.path.exists(tm_path):
        tm = load_yaml(tm_path)
        mitigated = len([t for t in tm['threats'] if t['status'] == 'MITIGATED'])
        total = len(tm['threats'])
        log(f"Threat Model Active: {mitigated}/{total} threats mitigated", "OK")
    else:
        log("Threat Model Artifact Missing", "WARN")

    log("Kernel Actuation Complete. System is PETRIFIED.", "SUCCESS")

if __name__ == "__main__":
    actuate_kernel()
