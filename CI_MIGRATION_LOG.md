# CI Migration Log

This document records the migration of the CI/CD pipeline to a consolidated GitHub Actions setup.

## 1. Removed Files
The following legacy or broken files were removed:

*   **Legacy CI Definitions:**
    *   `Jenkinsfile`
    *   `.gitlab-ci.yml`
*   **Package Management:**
    *   `package-lock.json` (Migrated to `pnpm-lock.yaml`)
*   **Broken/Redundant GitHub Workflows:**
    *   `.github/workflows/ci.yml` (Truncated/Broken)
    *   `.github/workflows/deploy.yml` (Replaced by `release.yml`)
    *   `.github/workflows/lint-diff-build-test.yml` (Replaced by `pr.yml` and `release.yml`)
    *   `.github/workflows/node.js.yml` (Redundant)
    *   `.github/workflows/python-package-conda.yml` (Broken reference to environment.yml)
    *   `.github/workflows/build-spine.yml` (Redundant)
    *   `.github/workflows/webpack.yml` (Redundant/npm-based)
    *   `.github/workflows/docs.yml` (Broken/npm-based)
    *   `.github/workflows/art.i.fact.yml` (Garbage content)
    *   `.github/workflows/checkpoint4dbl` (Garbage content)
    *   `.github/workflows/main.yml` (Link content)

## 2. Migrated Logic

| Original Source | Destination | Description |
| :--- | :--- | :--- |
| `Jenkinsfile` / `.gitlab-ci.yml` | `.github/workflows/release.yml` | Deployment logic calling `scripts/deploy.sh`, `RENDERER_URL` handling, Artifact collection. |
| `lint-diff-build-test.yml` | `.github/workflows/release.yml` | Docker Build & Push, SBOM generation (Syft), Image Signing (Cosign), Release Creation. |
| `lint-diff-build-test.yml` | `.github/workflows/pr.yml` | OpenAPI Spectral Linting and Diffing. |
| `deploy.yml` | `.github/workflows/release.yml` | Deployment steps (consolidated). |

## 3. Final Workflows

*   **`pr.yml`**: Runs on Pull Requests to `main`.
    *   Installs dependencies (pnpm).
    *   Runs `turbo run lint test build`.
    *   Performs OpenAPI linting and diffing against `main`.
*   **`release.yml`**: Runs on Push to `main` or Manual Dispatch.
    *   Installs dependencies (pnpm).
    *   Runs `turbo run build`.
    *   Builds and Pushes Docker image to GHCR.
    *   Generates SBOM and Signs the image.
    *   Deploys using `scripts/deploy.sh`.
    *   Collects artifacts (ledger, out, SBOM, sigs).
    *   Creates a GitHub Release with assets.

## 4. Invariants

*   **CI SSOT**: GitHub Actions is the Single Source of Truth for CI/CD.
*   **Package Manager**: `pnpm` is the authoritative package manager. `pnpm-lock.yaml` is the lockfile.
*   **Deployment Script**: `scripts/deploy.sh` is the authoritative deployment script.
