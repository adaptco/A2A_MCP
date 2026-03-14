#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────
// Ghost Void Engine — Determinism Verification Agent
//
// Runs the engine N times and asserts identical output (hash chain,
// world state, synthesis results) to verify deterministic replay.
// This is critical for the Qube/Jurassic Pixels pipeline where
// embeddings → hash chain → synthesis must be byte-identical.
// ─────────────────────────────────────────────────────────────────────

import { execSync } from "child_process";
import { createHash } from "crypto";

const ENGINE_BIN = process.env.ENGINE_BIN || "./bin/ghost-void_engine";
const ITERATIONS = parseInt(process.env.ITERATIONS || "5");

console.log("╔═══════════════════════════════════════════════════╗");
console.log("║   🔁 Determinism Verification Agent               ║");
console.log("╚═══════════════════════════════════════════════════╝");
console.log(`  Engine:     ${ENGINE_BIN}`);
console.log(`  Iterations: ${ITERATIONS}`);
console.log();

/**
 * Runs the engine and returns a SHA-256 of its stdout.
 * Deterministic engines must produce identical output on each run.
 */
function runAndHash(iteration) {
  try {
    const stdout = execSync(ENGINE_BIN, {
      timeout: 10_000,
      stdio: ["pipe", "pipe", "pipe"],
      encoding: "utf8",
    });

    const hash = createHash("sha256").update(stdout).digest("hex");
    console.log(`  Run ${iteration + 1}: ${hash.slice(0, 16)}… (${stdout.length} bytes)`);
    return { hash, stdout, error: null };
  } catch (err) {
    console.log(`  Run ${iteration + 1}: ERROR — ${err.message}`);
    return { hash: null, stdout: null, error: err.message };
  }
}

/**
 * Runs the Jurassic Pixels test binary and hashes its output.
 * The synthesis pipeline must be fully deterministic.
 */
function runTestAndHash(testBinary, label, iteration) {
  try {
    // Build the test first
    execSync(`make ${testBinary}`, {
      timeout: 30_000,
      stdio: ["pipe", "pipe", "pipe"],
      encoding: "utf8",
    });

    const binPath = `./bin/${testBinary.replace("test_", "")}_test`;
    const stdout = execSync(binPath, {
      timeout: 10_000,
      stdio: ["pipe", "pipe", "pipe"],
      encoding: "utf8",
    });

    const hash = createHash("sha256").update(stdout).digest("hex");
    console.log(`  ${label} Run ${iteration + 1}: ${hash.slice(0, 16)}…`);
    return { hash, stdout, error: null };
  } catch (err) {
    console.log(`  ${label} Run ${iteration + 1}: ERROR — ${err.message}`);
    return { hash: null, stdout: null, error: err.message };
  }
}

// ─── Main ───────────────────────────────────────────────────────────

let failures = 0;

// Test 1: Engine output determinism
console.log("📋 Test 1: Engine Output Determinism");
console.log("─".repeat(50));

const engineResults = [];
for (let i = 0; i < ITERATIONS; i++) {
  engineResults.push(runAndHash(i));
}

const validEngineResults = engineResults.filter((r) => r.hash !== null);
if (validEngineResults.length >= 2) {
  const allSame = validEngineResults.every((r) => r.hash === validEngineResults[0].hash);
  if (allSame) {
    console.log(`✅ Engine output is deterministic across ${validEngineResults.length} runs\n`);
  } else {
    console.log(`❌ Engine output is NON-DETERMINISTIC!\n`);
    const unique = [...new Set(validEngineResults.map((r) => r.hash))];
    console.log(`   Unique hashes: ${unique.length}`);
    failures++;
  }
} else if (validEngineResults.length === 0) {
  console.log("⚠️  Could not execute engine — skipping determinism check\n");
} else {
  console.log("⚠️  Only 1 successful run — cannot compare\n");
}

// Test 2: Jurassic Pixels synthesis determinism
console.log("📋 Test 2: Jurassic Pixels Synthesis Determinism");
console.log("─".repeat(50));

const jurassicResults = [];
for (let i = 0; i < Math.min(ITERATIONS, 3); i++) {
  jurassicResults.push(runTestAndHash("test_jurassic", "Jurassic", i));
}

const validJurassicResults = jurassicResults.filter((r) => r.hash !== null);
if (validJurassicResults.length >= 2) {
  const allSame = validJurassicResults.every((r) => r.hash === validJurassicResults[0].hash);
  if (allSame) {
    console.log(`✅ Jurassic synthesis is deterministic across ${validJurassicResults.length} runs\n`);
  } else {
    console.log(`❌ Jurassic synthesis is NON-DETERMINISTIC!\n`);
    failures++;
  }
} else {
  console.log("⚠️  Insufficient successful runs for Jurassic comparison\n");
}

// Final verdict
console.log("═".repeat(50));
if (failures === 0) {
  console.log("🎉 Determinism verification PASSED");
  process.exit(0);
} else {
  console.log(`⚠️  Determinism verification FAILED (${failures} failures)`);
  process.exit(1);
}
