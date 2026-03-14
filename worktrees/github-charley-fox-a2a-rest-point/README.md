# Container Workspace

This repository bootstraps `C:\Users\eqhsp\Downloads\Container` as a clean project root for the existing artifacts, runtime contracts, deployment scripts, and UI work already present in the folder.

## What lives here

- `shared/` contains the primary Vite artifact UI and is the fastest way to start working locally.
- `runtime/` contains scenario and WASM control artifacts.
- `scripts/` contains deployment and validation utilities.
- `k8s/` contains staging and production manifests.
- `Dynamical-Agent-Runner/Dynamical-Agent-Runner/` is an embedded local application tree used by Docker Compose and treated as an external working tree for now.

## Quick start

Install the shared UI dependencies if needed:

```powershell
npm install --prefix shared
```

Install the Python dependency used by the validation scripts:

```powershell
python -m pip install -r requirements.txt
```

Start the primary UI from the repo root:

```powershell
npm start
```

Build the UI:

```powershell
npm run build
```

Start the containerized runner stack:

```powershell
npm run compose:up
```

## Validation

Run the existing validation scripts from the repo root:

```powershell
npm run validate:workflows
npm run validate:runtime
```

## Notes

This bootstrap intentionally keeps loose media, downloads, archives, and generated output out of Git so the repo can start cleanly on `main`. If you decide to promote specific artifacts into source files later, move them into a versioned directory and remove the matching ignore rule.
