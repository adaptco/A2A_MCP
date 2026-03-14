Original prompt: PLEASE IMPLEMENT THIS PLAN:
# Simulator Route + Hybrid Runtime Loop
...

## 2026-03-10
- Initialized progress tracking for simulator-route implementation.
- Current repo state before edits: no existing frontend-specific progress handoff file, `frontend` and `game-validation.yml` clean in targeted paths.
- Replaced the standalone simulator HTML entry with a Vite/React root and removed the duplicate `frontend/public/index.html` entrypoint.
- Added typed simulator state, local stepping helpers, runtime API adapter, and a simulator-first app shell.
- First frontend build found only simulator-local issues: missing `three` typings and two implicit-any callbacks in scene cleanup.
- TODO:
  - Finish dependency/type cleanup and get `frontend` building.
  - Vendor the smoke client/actions needed for repo-local CI usage.
  - Update CI workflow and run Playwright validation against the simulator default route.
