.PHONY: freeze listener post verify seal qube-stage qube-seal qube-export echo-flare review canary promote rollback fossilize frontier-index frontier-cards frontier-tokens

PYTHON ?= python3

FRONTIER_INDEX_TOOL := scripts/build_frontier_agent_index.py
FRONTIER_INDEX_OUT := registry/agents/frontier_agent_index.v1.json
FRONTIER_CARDS_OUT := registry/agents/frontier_agent_cards.v1.json
FRONTIER_TOKENS_OUT := runtime/rbac/frontier_rbac_tokens.local.json
FRONTIER_TOKEN_ISSUER ?= mcp://a2a/rbac
FRONTIER_TOKEN_TTL_HOURS ?= 24

QUBE_DRAFT ?= capsule.patentDraft.qube.v1.json
QUBE_EXPORT_REQ ?= capsule.export.qubePatent.v1.request.json
FROZEN_DRAFT := runtime/frozen/$(notdir $(QUBE_DRAFT))
FREEZE_MANIFEST := runtime/freeze_manifest.json
FREEZE_REQUIREMENTS := freeze_capsules.sh scripts/canonicalize_manifest.py

freeze: $(FROZEN_DRAFT)

$(FROZEN_DRAFT): $(QUBE_DRAFT) $(FREEZE_REQUIREMENTS)
	@ts="$$(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
	  echo "🥶 Freezing QUBE draft capsule → $(QUBE_DRAFT)"; \
	  if [ ! -f "$(QUBE_DRAFT)" ]; then \
	    jq -n '{capsule_id:"capsule.patentDraft.qube.v1", qube:{}, lineage:{}, integrity:{}, meta:{}}' > "$(QUBE_DRAFT)"; \
	  fi; \
	  tmp=$$(mktemp); \
	  jq --arg ts "$$ts" '.capsule_id="capsule.patentDraft.qube.v1" | (.meta //= {}) | .meta.issued_at=$$ts | .issued_at=$$ts' "$(QUBE_DRAFT)" > "$$tmp" && mv "$$tmp" "$(QUBE_DRAFT)"; \
	  ./freeze_capsules.sh "$(QUBE_DRAFT)"

post: $(FROZEN_DRAFT)
	@echo "📮 Recording QUBE freeze manifest entry"
	@if [ ! -f "$(FREEZE_MANIFEST)" ]; then \
	  echo "Freeze manifest not found at $(FREEZE_MANIFEST)" >&2; \
	  exit 1; \
	fi; \
	if ! jq -e '."$(FROZEN_DRAFT)"' "$(FREEZE_MANIFEST)" >/dev/null; then \
	  echo "Frozen capsule digest missing from $(FREEZE_MANIFEST)" >&2; \
	  exit 1; \
	fi

verify: $(FROZEN_DRAFT)
	@echo "🧪 Verifying QUBE freeze manifest integrity"
	@if [ ! -f "$(FREEZE_MANIFEST)" ]; then \
	  echo "Freeze manifest not found at $(FREEZE_MANIFEST)" >&2; \
	  exit 1; \
	fi; \
	manifest_digest=$$(jq -r '."$(FROZEN_DRAFT)" // empty' "$(FREEZE_MANIFEST)"); \
	if [ -z "$$manifest_digest" ]; then \
	  echo "Frozen capsule digest missing from $(FREEZE_MANIFEST)" >&2; \
	  exit 1; \
	fi; \
	actual_digest=$$(sha256sum "$(FROZEN_DRAFT)" | cut -d' ' -f1); \
	if [ "$$manifest_digest" != "$$actual_digest" ]; then \
	  echo "Digest mismatch for $(FROZEN_DRAFT): $$actual_digest != $$manifest_digest" >&2; \
	  exit 1; \
	fi

seal: verify
	@ts="$$(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
	  echo "🔏 Stamping QUBE federation receipt → capsule.federation.receipt.v1.json"; \
	  manifest_digest=$$(jq -r '."$(FROZEN_DRAFT)" // empty' "$(FREEZE_MANIFEST)"); \
	  if [ -z "$$manifest_digest" ]; then \
	    echo "Frozen capsule digest missing from $(FREEZE_MANIFEST)" >&2; \
	    exit 1; \
	  fi; \
	  if [ ! -f "capsule.federation.receipt.v1.json" ]; then \
	    jq -n '{capsule_id:"capsule.federation.receipt.v1", receipts:[]}' > capsule.federation.receipt.v1.json; \
	  fi; \
	  tmp=$$(mktemp); \
	  jq --arg path "$(FROZEN_DRAFT)" --arg digest "$$manifest_digest" --arg ts "$$ts" '(.receipts //= []) | (.receipts = ((.receipts | map(select(.capsule_path != $$path))) + [{capsule_path:$$path, digest:$$digest, issued_at:$$ts}]))' capsule.federation.receipt.v1.json > "$$tmp" && mv "$$tmp" capsule.federation.receipt.v1.json


qube-stage: freeze post verify
	@echo "📜 Staging QUBE draft capsule → $(QUBE_DRAFT)"

qube-seal: qube-stage seal
	@echo "🔏 QUBE draft sealed; see capsule.federation.receipt.v1.json"

qube-export: qube-seal
	@ts="$$(date -u +%Y-%m-%dT%H:%M:%SZ)"; \
	  echo "🚚 Emitting DAO export request → $(QUBE_EXPORT_REQ)"; \
	  if [ ! -f "$(QUBE_EXPORT_REQ)" ]; then \
	    jq -n '{protocol:"capsule.export.qubePatent.v1",format:"artifactBundle",emails:[]}' > "$(QUBE_EXPORT_REQ)"; \
	  fi; \
	  tmp=$$(mktemp); \
	  jq --arg ts "$$ts" '(.dao //= {}) | (.meta //= {}) | .meta.issued_at=$$ts | .dao.protocol="capsule.export.qubePatent.v1" | .dao.format=(.dao.format // "artifactBundle") | (.dao.integrity //= {}) | .dao.integrity.attestation_quorum=(.dao.integrity.attestation_quorum // "2-of-3")' "$(QUBE_EXPORT_REQ)" > "$$tmp" && mv "$$tmp" "$(QUBE_EXPORT_REQ)"

echo-flare:
	@echo "📡 Emitting echoFlare resonance map → capsule.echoFlare.qube.v1.json"
	@jq -n '{capsule_id:"capsule.echoFlare.qube.v1", contributors:[]}' > capsule.echoFlare.qube.v1.json

REVIEW_MANIFEST := capsules/governance/capsule.concept.arch.review.v1.json
REVIEW_TOOL := scripts/concept_arch_review.py
REVIEW_SCENARIO_DIR := manifests/concept_architecture

review:
	@$(PYTHON) $(REVIEW_TOOL) --manifest $(REVIEW_MANIFEST) review --scenario $(REVIEW_SCENARIO_DIR)/review.json

canary:
	@$(PYTHON) $(REVIEW_TOOL) --manifest $(REVIEW_MANIFEST) canary --scenario $(REVIEW_SCENARIO_DIR)/canary.json

promote:
	@$(PYTHON) $(REVIEW_TOOL) --manifest $(REVIEW_MANIFEST) promote --scenario $(REVIEW_SCENARIO_DIR)/promote.json

rollback:
	@$(PYTHON) $(REVIEW_TOOL) --manifest $(REVIEW_MANIFEST) rollback --scenario $(REVIEW_SCENARIO_DIR)/rollback.json

fossilize:
	@$(PYTHON) $(REVIEW_TOOL) --manifest $(REVIEW_MANIFEST) fossilize --scenario $(REVIEW_SCENARIO_DIR)/fossilize.json

frontier-index:
	@$(PYTHON) $(FRONTIER_INDEX_TOOL) --index-out $(FRONTIER_INDEX_OUT) --cards-out $(FRONTIER_CARDS_OUT) --tokens-out $(FRONTIER_TOKENS_OUT) --issuer "$(FRONTIER_TOKEN_ISSUER)" --ttl-hours $(FRONTIER_TOKEN_TTL_HOURS)
	@echo "Frontier agent index generated at $(FRONTIER_INDEX_OUT)"
	@echo "RBAC token bundle generated at $(FRONTIER_TOKENS_OUT)"

frontier-cards: frontier-index
	@echo "Frontier agent cards refreshed at $(FRONTIER_CARDS_OUT)"

frontier-tokens: frontier-index
	@echo "Frontier RBAC tokens refreshed at $(FRONTIER_TOKENS_OUT)"
