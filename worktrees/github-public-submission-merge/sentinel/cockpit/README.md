# Sentinel cockpit

The cockpit is the operator-facing HUD that visualizes capsule state, bindings, and ledger hashes.

## Assets
- **Primary dashboard** – `public/hud/capsules/avatar/index.html` renders the Sovereign Fleet Architect dashboard with Tailwind
  and Chart.js overlays.
- **Merkle viewer** – `public/hud/capsules/capsule_cockpit.html` provides a drag-and-drop inspector for ledger batch manifests.
- **Data feed** – `public/data/avatar_bindings.v1.json` is the manifest served to the dashboard.

## Serving locally
`app/server.py` exposes a minimal HTTP server that responds on `/health` and can be extended to serve the static HUD assets.
Operators can run it directly while iterating on cockpit changes:

```bash
python app/server.py
```

With the server running, open the HTML assets from the `public/hud/` tree in a browser to review cockpit behaviour against the
latest manifest snapshot.
