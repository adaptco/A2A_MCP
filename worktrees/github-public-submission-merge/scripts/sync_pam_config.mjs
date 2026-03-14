import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const sourcePath = path.join(repoRoot, "agents", "pam_orchestrator.json");
const targetPath = path.join(
  repoRoot,
  "apps",
  "api",
  "src",
  "config",
  "pam_orchestrator.json",
);

fs.mkdirSync(path.dirname(targetPath), { recursive: true });
fs.copyFileSync(sourcePath, targetPath);
process.stdout.write(`${targetPath}\n`);
