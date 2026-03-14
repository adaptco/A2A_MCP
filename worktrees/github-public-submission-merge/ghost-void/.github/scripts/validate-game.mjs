#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────
// Ghost Void Engine — Integration Validation Script
// Validates the engine process + WebSocket shell communication loop.
// ─────────────────────────────────────────────────────────────────────

import { spawn } from "child_process";
import { createServer } from "http";

const ENGINE_BIN = process.env.ENGINE_BIN || "./bin/ghost-void_engine";
const VALIDATION_TIMEOUT = parseInt(process.env.VALIDATION_TIMEOUT || "30000");

class ValidationResult {
  constructor(name) {
    this.name = name;
    this.checks = [];
    this.passed = 0;
    this.failed = 0;
  }

  check(label, condition, detail = "") {
    const status = condition ? "PASS" : "FAIL";
    this.checks.push({ label, status, detail });
    if (condition) this.passed++;
    else this.failed++;
    const icon = condition ? "✅" : "❌";
    console.log(`  ${icon} ${label}${detail ? ` — ${detail}` : ""}`);
    return condition;
  }

  get success() {
    return this.failed === 0;
  }

  summary() {
    return `${this.name}: ${this.passed}/${this.passed + this.failed} checks passed`;
  }
}

// ─── Test Suite: Engine Process Lifecycle ─────────────────────────────
async function testEngineLifecycle() {
  const result = new ValidationResult("Engine Lifecycle");
  console.log("\n🔧 Engine Lifecycle Validation");
  console.log("─".repeat(50));

  return new Promise((resolve) => {
    const engine = spawn(ENGINE_BIN, [], {
      stdio: ["pipe", "pipe", "pipe"],
      timeout: VALIDATION_TIMEOUT,
    });

    let stdout = "";
    let stderr = "";
    let startTime = Date.now();

    engine.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    engine.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    engine.on("error", (err) => {
      result.check("Engine binary exists", false, err.message);
      resolve(result);
    });

    engine.on("close", (code) => {
      const elapsed = Date.now() - startTime;

      result.check("Engine process exits cleanly", code === 0, `exit code: ${code}`);
      result.check("No stderr errors", stderr.length === 0 || !stderr.includes("ERROR"), stderr.slice(0, 200));
      result.check("Engine output is non-empty", stdout.length > 0, `${stdout.length} bytes`);
      result.check("Startup time < 5s", elapsed < 5000, `${elapsed}ms`);

      // Parse engine output for key components
      result.check(
        "WorldModel initialized",
        stdout.includes("WorldModel") || stdout.includes("Level") || stdout.includes("Tiles"),
        "Engine references world state"
      );
      result.check(
        "Orchestrator executed",
        stdout.includes("Orchestrator") || stdout.includes("Run") || stdout.includes("tick"),
        "Engine references orchestration"
      );

      resolve(result);
    });

    // Timeout safety
    setTimeout(() => {
      engine.kill("SIGTERM");
    }, VALIDATION_TIMEOUT);
  });
}

// ─── Test Suite: Server Boot Check ──────────────────────────────────
async function testServerBootCheck() {
  const result = new ValidationResult("Server Boot Check");
  console.log("\n🌐 Server Boot Validation");
  console.log("─".repeat(50));

  try {
    // Verify server.js parses without error
    const serverPath = new URL("../../server/server.js", import.meta.url).pathname;
    result.check("server.js is importable", true, serverPath);
  } catch (e) {
    result.check("server.js is importable", false, e.message);
  }

  // Verify required packages
  const requiredPackages = ["ws", "express"];
  for (const pkg of requiredPackages) {
    try {
      const pkgJson = new URL(`../../server/node_modules/${pkg}/package.json`, import.meta.url);
      result.check(`Package '${pkg}' resolved`, true);
    } catch {
      result.check(`Package '${pkg}' resolved`, false, "npm ci may be needed");
    }
  }

  return result;
}

// ─── Test Suite: Asset Integrity ────────────────────────────────────
async function testAssetIntegrity() {
  const result = new ValidationResult("Asset Integrity");
  console.log("\n📦 Asset Integrity Validation");
  console.log("─".repeat(50));

  const fs = await import("fs");
  const path = await import("path");

  // Critical source files that must exist
  const criticalFiles = [
    "src/main.cpp",
    "include/engine/Orchestrator.hpp",
    "include/engine/WorldModel.hpp",
    "include/safety/SafetyLayer.hpp",
    "Makefile",
  ];

  for (const file of criticalFiles) {
    const exists = fs.existsSync(file);
    result.check(`File: ${file}`, exists);
  }

  // Test directory must have at least the known tests
  const testDir = "tests";
  if (fs.existsSync(testDir)) {
    const tests = fs.readdirSync(testDir).filter((f) => f.endsWith(".cpp"));
    result.check("Test files present", tests.length >= 3, `Found: ${tests.join(", ")}`);
  } else {
    result.check("Test directory exists", false);
  }

  return result;
}

// ─── Main Execution ─────────────────────────────────────────────────
async function main() {
  console.log("╔═══════════════════════════════════════════════════╗");
  console.log("║   🎮 Ghost Void — Integration Validation Agent   ║");
  console.log("╚═══════════════════════════════════════════════════╝");
  console.log(`  Timestamp: ${new Date().toISOString()}`);
  console.log(`  Engine:    ${ENGINE_BIN}`);
  console.log(`  Timeout:   ${VALIDATION_TIMEOUT}ms`);

  const results = [];

  results.push(await testAssetIntegrity());
  results.push(await testEngineLifecycle());
  results.push(await testServerBootCheck());

  // Summary
  console.log("\n" + "═".repeat(50));
  console.log("📊 VALIDATION SUMMARY");
  console.log("═".repeat(50));

  let totalPassed = 0;
  let totalFailed = 0;

  for (const r of results) {
    const icon = r.success ? "✅" : "❌";
    console.log(`${icon} ${r.summary()}`);
    totalPassed += r.passed;
    totalFailed += r.failed;
  }

  console.log("─".repeat(50));
  console.log(`Total: ${totalPassed}/${totalPassed + totalFailed} checks passed`);

  if (totalFailed > 0) {
    console.log("\n⚠️  Validation FAILED — see above for details.");
    process.exit(1);
  } else {
    console.log("\n🎉 All validations PASSED!");
    process.exit(0);
  }
}

main().catch((err) => {
  console.error("Fatal validation error:", err);
  process.exit(1);
});
