# GitHub workflow catalog

The Sentinel relies on repository automation to enforce governance policy. The `.github/workflows/` directory contains the
following key pipelines:

- `avatar-bindings-ci.yml` – runs schema validation, canonicalization, Ed25519 signing, and commits sealed ledger artifacts when
  main receives a push.
- `avatar-bindings-governance.yml` – executes the freeze script against golden fixtures to prove manifests fail or pass as
  expected and publishes the canonical/hash/signature trio.
- `ci.yml` – lint and diff the OpenAPI contract, build and sign the container image, execute smoke tests, and append audit
  events to the ledger on successful pushes.
- `cockpit-dispatch-handler.yml` – responds to `repository_dispatch` hooks for freeze, override, and review requests by invoking
  the Python governance handlers and committing ledger updates.
- `fonts-proxy-ci-cd.yml` – coordinates the fonts proxy CI run, logs events with `hash_gen_scroll.py`, validates the ledger event
  log, and archives the generated NDJSON traces.

Update this catalog whenever new governance jobs are introduced so Sentinel operators have a single index of enforcement hooks.
