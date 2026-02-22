# Sentinel architecture

The Sentinel stitches together protocol capsules, validation rails, and the Live Ops cockpit into a single enforcement mesh.
It is composed of the following flows:

1. **Capsule source of truth** – Capsule descriptors such as
   `capsules/doctrine/capsule.attestation.scroll.v1.json` bind governance capsules to HUD entry points and ledger events.
2. **Manifest governance** – The freeze toolchain under `scripts/` and the canonical artifacts in `governance/` provide the
   canonical, hashed, and signed manifests used by automation.
3. **Automated review** – GitHub workflows in `.github/workflows/` run schema validation, canonicalization, and signing steps to
   keep freezes deterministic before anything is promoted to production.
4. **Ledger attestation** – `hash_gen_scroll.py` produces Merkle rooted batches under `sentinel/ledger/batches/` and emits
   NDJSON events for long-lived audit trails under `sentinel/ledger/events/`.
5. **Live Ops cockpit** – The HUD assets inside `public/hud/` and manifest data in `public/data/avatar_bindings.v1.json` are
   served by the lightweight HTTP shim in `app/server.py` to deliver the operator experience.
6. **SSoT validation** – The Adaptco SSoT microservice (`adaptco-ssot/`) holds the persisted catalog and schema definitions that
   upstream pipelines query before building manifests, ensuring SSOT parity.

These loops together let the Sentinel enforce protocol integrity while giving operators real-time feedback through the cockpit.
