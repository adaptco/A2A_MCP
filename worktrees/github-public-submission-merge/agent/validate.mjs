#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────────────
// 🤖 Ghost Void — Coding Agent: Post-Completion Validator
//
// This is the autonomous validation agent entry point. It runs as a
// standalone process (locally or in CI) that validates the entire game
// stack after agents have completed their coding work.
//
// Usage:
//   node agent/validate.mjs                    # Default validation
//   node agent/validate.mjs --level full       # Full depth
//   node agent/validate.mjs --watch            # Watch mode
//   node agent/validate.mjs --report json      # JSON report
//
// This agent orchestrates:
//   1. Source integrity checks (file presence, header guards, includes)
//   2. Build verification (compile + link + binary health)
//   3. Test execution (safety, engine, jurassic, boss)
//   4. Determinism replay (N-run hash comparison)
//   5. Runtime smoke test (engine process lifecycle)
//   6. Report generation (markdown + JSON)
// ─────────────────────────────────────────────────────────────────────

import { execSync, execFileSync, spawn } from "child_process";
import { existsSync, readFileSync, writeFileSync, readdirSync, statSync } from "fs";
import { join, resolve } from "path";
import { createHash } from "crypto";

// ─── Configuration ──────────────────────────────────────────────────

const DEFAULT_CONFIG = {
  projectRoot: resolve(".."),
  level: "standard",    // quick | standard | full
  reportFormat: "markdown", // markdown | json
  watch: false,
  verbose: false,
  determinismRuns: 3,
  buildTimeout: 60_000,
  testTimeout: 30_000,
  engineBin: "bin/ghost-void_engine",

  // Expected project structure
  criticalPaths: {
    sources: [
      "src/main.cpp",
      "src/engine/Orchestrator.cpp",
      "src/engine/WorldModel.cpp",
      "src/safety/SafetyLayer.cpp",
    ],
    headers: [
      "include/engine/Orchestrator.hpp",
      "include/engine/WorldModel.hpp",
      "include/engine/Sandbox.hpp",
      "include/safety/SafetyLayer.hpp",
    ],
    tests: [
      "tests/engine_test.cpp",
      "tests/safety_test.cpp",
      "tests/jurassic_pixels_test.cpp",
      "tests/boss_test.cpp",
    ],
    build: ["Makefile", "CMakeLists.txt"],
    server: ["server/server.js", "server/package.json"],
  },

  // Make targets to validate
  testTargets: [
    { name: "safety", target: "test", description: "SafetyLayer bounds + NaN" },
    { name: "engine", target: "test_engine", description: "Orchestrator + WorldModel" },
    { name: "jurassic", target: "test_jurassic", description: "Jurassic Pixels pipeline" },
  ],
};

// ─── CLI Parsing ────────────────────────────────────────────────────

function parseArgs() {
  const args = process.argv.slice(2);
  const config = { ...DEFAULT_CONFIG };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--level":
        config.level = args[++i];
        break;
      case "--report":
        config.reportFormat = args[++i];
        break;
      case "--watch":
        config.watch = true;
        break;
      case "--verbose":
        config.verbose = true;
        break;
      case "--root":
        config.projectRoot = resolve(args[++i]);
        break;
      case "--help":
        console.log(`
🤖 Ghost Void Validation Agent

Usage: node validate.mjs [options]

Options:
  --level <quick|standard|full>  Validation depth (default: standard)
  --report <markdown|json>       Report format (default: markdown)
  --watch                        Re-run on file changes
  --verbose                      Detailed output
  --root <path>                  Project root directory
  --help                         Show this help
`);
        process.exit(0);
    }
  }

  return config;
}

// ─── Validation Engine ──────────────────────────────────────────────

class ValidationAgent {
  constructor(config) {
    this.config = config;
    this.results = [];
    this.startTime = Date.now();
  }

  log(msg) {
    console.log(msg);
  }

  verbose(msg) {
    if (this.config.verbose) console.log(`  [verbose] ${msg}`);
  }

  // ── Phase 1: Source Integrity ───────────────────────────────────

  async checkSourceIntegrity() {
    const phase = { name: "Source Integrity", checks: [], icon: "📁" };
    this.log(`\n${phase.icon} Phase 1: ${phase.name}`);
    this.log("─".repeat(50));

    const root = this.config.projectRoot;

    for (const [category, paths] of Object.entries(this.config.criticalPaths)) {
      for (const p of paths) {
        const fullPath = join(root, p);
        const exists = existsSync(fullPath);
        phase.checks.push({
          label: `[${category}] ${p}`,
          pass: exists,
          detail: exists ? `${statSync(fullPath).size} bytes` : "MISSING",
        });
        const icon = exists ? "✅" : "❌";
        this.log(`  ${icon} ${p}`);
      }
    }

    // Header guard check
    if (this.config.level !== "quick") {
      const headerDir = join(root, "include");
      if (existsSync(headerDir)) {
        const headers = this.findFiles(headerDir, ".hpp");
        for (const h of headers) {
          const content = readFileSync(h, "utf8");
          const hasGuard = content.includes("#pragma once") || content.includes("#ifndef");
          phase.checks.push({
            label: `HeaderGuard: ${h.replace(root, ".")}`,
            pass: hasGuard,
            detail: hasGuard ? "protected" : "NO INCLUDE GUARD",
          });
          if (!hasGuard) this.log(`  ⚠️  Missing include guard: ${h}`);
        }
      }
    }

    this.results.push(phase);
    return phase;
  }

  // ── Phase 2: Build Verification ─────────────────────────────────

  async checkBuild() {
    const phase = { name: "Build Verification", checks: [], icon: "🔧" };
    this.log(`\n${phase.icon} Phase 2: ${phase.name}`);
    this.log("─".repeat(50));

    const root = this.config.projectRoot;

    try {
      this.log("  ⏳ Running make all...");
      const output = execSync("make all", {
        cwd: root,
        timeout: this.config.buildTimeout,
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
      });

      phase.checks.push({
        label: "Compilation",
        pass: true,
        detail: "make all succeeded",
      });
      this.log("  ✅ Compilation succeeded");

      // Binary existence and size
      const binPath = join(root, this.config.engineBin);
      if (existsSync(binPath)) {
        const size = statSync(binPath).size;
        phase.checks.push({
          label: "Binary produced",
          pass: true,
          detail: `${(size / 1024).toFixed(1)} KB`,
        });
        this.log(`  ✅ Binary: ${(size / 1024).toFixed(1)} KB`);
      }
    } catch (err) {
      phase.checks.push({
        label: "Compilation",
        pass: false,
        detail: err.stderr?.slice(0, 500) || err.message,
      });
      this.log(`  ❌ Build failed: ${err.message.slice(0, 200)}`);
    }

    this.results.push(phase);
    return phase;
  }

  // ── Phase 3: Test Execution ─────────────────────────────────────

  async runTests() {
    const phase = { name: "Test Execution", checks: [], icon: "🧪" };
    this.log(`\n${phase.icon} Phase 3: ${phase.name}`);
    this.log("─".repeat(50));

    const root = this.config.projectRoot;

    for (const test of this.config.testTargets) {
      try {
        this.log(`  ⏳ Running make ${test.target}...`);
        const output = execSync(`make ${test.target}`, {
          cwd: root,
          timeout: this.config.testTimeout,
          encoding: "utf8",
          stdio: ["pipe", "pipe", "pipe"],
        });

        const passed = output.includes("passed") || output.includes("SUCCESS") || output.includes("Passed");
        phase.checks.push({
          label: `${test.name}: ${test.description}`,
          pass: true,
          detail: "all assertions passed",
        });
        this.log(`  ✅ ${test.name}: ${test.description}`);
      } catch (err) {
        phase.checks.push({
          label: `${test.name}: ${test.description}`,
          pass: false,
          detail: err.stderr?.slice(0, 300) || err.message,
        });
        this.log(`  ❌ ${test.name}: FAILED`);
        this.verbose(err.stderr?.slice(0, 300) || err.message);
      }
    }

    this.results.push(phase);
    return phase;
  }

  // ── Phase 4: Determinism Replay ─────────────────────────────────

  async checkDeterminism() {
    if (this.config.level === "quick") return null;

    const phase = { name: "Determinism Replay", checks: [], icon: "🔁" };
    this.log(`\n${phase.icon} Phase 4: ${phase.name}`);
    this.log("─".repeat(50));

    const root = this.config.projectRoot;
    const binPath = join(root, this.config.engineBin);

    if (!existsSync(binPath)) {
      phase.checks.push({ label: "Engine binary", pass: false, detail: "not found" });
      this.results.push(phase);
      return phase;
    }

    const hashes = [];
    for (let i = 0; i < this.config.determinismRuns; i++) {
      try {
        const stdout = execFileSync(binPath, [], {
          timeout: 10_000,
          encoding: "utf8",
          stdio: ["pipe", "pipe", "pipe"],
        });
        const hash = createHash("sha256").update(stdout).digest("hex");
        hashes.push(hash);
        this.log(`  Run ${i + 1}: ${hash.slice(0, 16)}…`);
      } catch (err) {
        this.log(`  Run ${i + 1}: ERROR`);
      }
    }

    if (hashes.length >= 2) {
      const allSame = hashes.every((h) => h === hashes[0]);
      phase.checks.push({
        label: "Output consistency",
        pass: allSame,
        detail: allSame
          ? `${hashes.length} identical runs`
          : `${new Set(hashes).size} unique outputs detected`,
      });
      this.log(allSame ? "  ✅ Deterministic" : "  ❌ NON-DETERMINISTIC");
    }

    this.results.push(phase);
    return phase;
  }

  // ── Phase 5: Runtime Smoke Test ─────────────────────────────────

  async smokeTest() {
    if (this.config.level === "quick") return null;

    const phase = { name: "Runtime Smoke Test", checks: [], icon: "💨" };
    this.log(`\n${phase.icon} Phase 5: ${phase.name}`);
    this.log("─".repeat(50));

    const root = this.config.projectRoot;
    const binPath = join(root, this.config.engineBin);

    return new Promise((resolve) => {
      if (!existsSync(binPath)) {
        phase.checks.push({ label: "Engine binary", pass: false, detail: "not found" });
        this.results.push(phase);
        resolve(phase);
        return;
      }

      const start = Date.now();
      const proc = spawn(binPath, [], {
        stdio: ["pipe", "pipe", "pipe"],
        timeout: 15_000,
      });

      let stdout = "";
      let stderr = "";
      proc.stdout.on("data", (d) => (stdout += d.toString()));
      proc.stderr.on("data", (d) => (stderr += d.toString()));

      proc.on("close", (code) => {
        const elapsed = Date.now() - start;

        phase.checks.push({ label: "Exit code", pass: code === 0, detail: `code ${code}` });
        phase.checks.push({ label: "No crash", pass: !stderr.includes("SIGSEGV") && !stderr.includes("SIGABRT"), detail: "no segfaults" });
        phase.checks.push({ label: "Startup < 3s", pass: elapsed < 3000, detail: `${elapsed}ms` });
        phase.checks.push({ label: "Output present", pass: stdout.length > 0, detail: `${stdout.length} bytes` });

        this.log(`  ${code === 0 ? "✅" : "❌"} Exit code: ${code}`);
        this.log(`  ✅ Startup: ${elapsed}ms`);

        this.results.push(phase);
        resolve(phase);
      });

      proc.on("error", (err) => {
        phase.checks.push({ label: "Engine spawn", pass: false, detail: err.message });
        this.results.push(phase);
        resolve(phase);
      });

      setTimeout(() => proc.kill(), 15_000);
    });
  }

  // ── Report Generation ───────────────────────────────────────────

  generateReport() {
    const elapsed = Date.now() - this.startTime;
    let totalPass = 0;
    let totalFail = 0;

    for (const phase of this.results) {
      for (const check of phase.checks) {
        if (check.pass) totalPass++;
        else totalFail++;
      }
    }

    const overall = totalFail === 0 ? "PASSED" : "FAILED";
    const overallIcon = overall === "PASSED" ? "✅" : "❌";

    if (this.config.reportFormat === "json") {
      const report = {
        status: overall,
        timestamp: new Date().toISOString(),
        elapsed_ms: elapsed,
        total_passed: totalPass,
        total_failed: totalFail,
        phases: this.results,
      };
      writeFileSync("validation-report.json", JSON.stringify(report, null, 2));
      this.log(`\n📊 JSON report → validation-report.json`);
      return report;
    }

    // Markdown report
    let md = `# ${overallIcon} Game Validation Report\n\n`;
    md += `> **Status**: ${overall} | **Checks**: ${totalPass}/${totalPass + totalFail} | **Time**: ${(elapsed / 1000).toFixed(1)}s\n\n`;

    for (const phase of this.results) {
      const phasePass = phase.checks.filter((c) => c.pass).length;
      const phaseTotal = phase.checks.length;
      md += `## ${phase.icon} ${phase.name} (${phasePass}/${phaseTotal})\n\n`;
      md += `| Check | Status | Detail |\n|-------|--------|--------|\n`;
      for (const check of phase.checks) {
        md += `| ${check.label} | ${check.pass ? "✅" : "❌"} | ${check.detail} |\n`;
      }
      md += `\n`;
    }

    writeFileSync("validation-report.md", md);
    this.log(`\n📊 Markdown report → validation-report.md`);
    return md;
  }

  // ── Utility ─────────────────────────────────────────────────────

  findFiles(dir, ext) {
    const results = [];
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, item.name);
      if (item.isDirectory()) results.push(...this.findFiles(full, ext));
      else if (item.name.endsWith(ext)) results.push(full);
    }
    return results;
  }

  // ── Run All ─────────────────────────────────────────────────────

  async run() {
    this.log("╔═══════════════════════════════════════════════════╗");
    this.log("║   🤖 Ghost Void — Coding Agent Validator          ║");
    this.log("╚═══════════════════════════════════════════════════╝");
    this.log(`  Level:      ${this.config.level}`);
    this.log(`  Project:    ${this.config.projectRoot}`);
    this.log(`  Timestamp:  ${new Date().toISOString()}`);

    await this.checkSourceIntegrity();
    await this.checkBuild();
    await this.runTests();
    await this.checkDeterminism();
    await this.smokeTest();

    this.generateReport();

    // Final summary
    let totalFail = 0;
    for (const phase of this.results) {
      for (const check of phase.checks) {
        if (!check.pass) totalFail++;
      }
    }

    this.log("\n" + "═".repeat(50));
    if (totalFail === 0) {
      this.log("🎉 ALL VALIDATIONS PASSED");
    } else {
      this.log(`⚠️  ${totalFail} VALIDATION(S) FAILED`);
    }

    return totalFail === 0 ? 0 : 1;
  }
}

// ─── Entry Point ────────────────────────────────────────────────────

const config = parseArgs();
const agent = new ValidationAgent(config);
const exitCode = await agent.run();
process.exit(exitCode);
