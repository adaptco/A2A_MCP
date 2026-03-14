#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const packageRoot = resolve(__dirname, '..');
const outputDir = join(packageRoot, 'deploy');

function sha256Hex(data) {
  return createHash('sha256').update(data).digest('hex');
}

async function run(cmd, args, cwd) {
  const { stdout, stderr } = await execFileAsync(cmd, args, { cwd });
  if (stderr?.trim()) {
    process.stderr.write(stderr);
  }
  return stdout;
}

async function main() {
  await mkdir(outputDir, { recursive: true });

  // Remove previous generated artifacts, but keep docs under deploy/ if any are added later.
  await rm(join(outputDir, 'manifest.json'), { force: true });
  await rm(join(outputDir, 'SHA256SUMS.txt'), { force: true });

  const allowStaleDistFallback = process.env.KERNEL_PACKAGE_ALLOW_STALE_DIST === '1';

  try {
    await run('npm', ['run', 'build'], packageRoot);
  } catch (error) {
    if (!allowStaleDistFallback) {
      throw error;
    }

    const distCheck = await readFile(join(packageRoot, 'dist', 'index.js'), 'utf8').catch(() => null);
    if (!distCheck) {
      throw error;
    }

    process.stderr.write(
      'Build step failed; KERNEL_PACKAGE_ALLOW_STALE_DIST=1 is set, reusing existing dist artifacts for packaging.\n',
    );
  }

  const packStdout = await run('npm', ['pack', '--json', '--pack-destination', outputDir], packageRoot);
  const packResult = JSON.parse(packStdout);
  if (!Array.isArray(packResult) || packResult.length === 0) {
    throw new Error('npm pack produced no output');
  }

  const artifact = packResult[0];
  const tarballName = basename(artifact.filename);
  const tarballPath = join(outputDir, tarballName);
  const tarballBytes = await readFile(tarballPath);

  const packageJson = JSON.parse(await readFile(join(packageRoot, 'package.json'), 'utf8'));

  const manifest = {
    package: packageJson.name,
    version: packageJson.version,
    artifact: tarballName,
    sha256: sha256Hex(tarballBytes),
    bytes: tarballBytes.byteLength,
    generated_at: new Date().toISOString(),
    files: artifact.files ?? [],
  };

  await writeFile(join(outputDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  await writeFile(join(outputDir, 'SHA256SUMS.txt'), `${manifest.sha256}  ${tarballName}\n`, 'utf8');

  process.stdout.write(`Deployment package created: ${tarballPath}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
