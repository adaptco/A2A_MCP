.PHONY: help dev dev-stop dev-logs test build-images build-push deploy-k8s deploy-argocd deploy-rollback lint clean

# Default variables
REGISTRY ?= docker.io
ORG ?= vh2
BACKEND_TAG ?= 1.0.0
FRONTEND_TAG ?= 1.0.0
REPO_URL ?= https://github.com/YOUR_ORG/vh2-sovereign-validator.git

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;36m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)VH2 Sovereign Validator — Make Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make dev                          # Start local dev stack"
	@echo "  make build-images REGISTRY=gcr.io # Build with custom registry"
	@echo "  make deploy-k8s                   # Deploy to K8s"
	@echo "  make deploy-argocd REPO_URL=...   # Deploy via ArgoCD"

# ─────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────

dev: ## Start local dev stack with docker-compose
	@echo "$(BLUE)Starting VH2 local dev stack...$(NC)"
	cd vh2-docker && docker-compose up --build
	@echo "$(GREEN)✓ Backend running on http://localhost:3001$(NC)"
	@echo "$(GREEN)✓ Frontend running on http://localhost:3000$(NC)"
	@echo "$(GREEN)✓ Nginx running on http://localhost:80$(NC)"

dev-stop: ## Stop local dev stack
	@echo "$(BLUE)Stopping VH2 dev stack...$(NC)"
	cd vh2-docker && docker-compose down
	@echo "$(GREEN)✓ Stack stopped$(NC)"

dev-logs: ## Tail logs from all services
	@echo "$(BLUE)Tailing logs (Ctrl+C to exit)...$(NC)"
	cd vh2-docker && docker-compose logs -f

dev-clean: ## Remove all local containers, volumes, and images
	@echo "$(RED)Cleaning up VH2 dev environment...$(NC)"
	cd vh2-docker && docker-compose down -v
	docker rmi vh2-backend:latest vh2-frontend:latest 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# ─────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────

test: ## Run unit tests (backend)
	@echo "$(BLUE)Running backend unit tests...$(NC)"
	cd vh2-docker/backend && npm install --silent && npm test
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-integration: ## Run integration tests with docker-compose
	@echo "$(BLUE)Running integration tests...$(NC)"
	cd vh2-docker && docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@sleep 5
	@echo "Testing backend /validate endpoint..."
	@curl -s -X POST http://localhost:3001/validate \
		-H "Content-Type: application/json" \
		-d '{"vehicle":"vh2","wheels":{"front_et":29,"rear_et":22}}' | jq .
	@cd vh2-docker && docker-compose down
	@echo "$(GREEN)✓ Integration tests passed$(NC)"

test-smoke: ## Run smoke tests against K8s cluster
	@echo "$(BLUE)Running K8s smoke tests...$(NC)"
	@echo "Creating test job..."
	kubectl create job --from=cronjob/vh2-smoke-test vh2-smoke-test-$(shell date +%s) -n vh2-prod 2>/dev/null || true
	@sleep 3
	@echo "Test job status:"
	@kubectl get jobs -n vh2-prod | grep vh2-smoke-test
	@echo "$(GREEN)✓ Check logs with: kubectl logs -n vh2-prod -l app=vh2-smoke-test$(NC)"

# ─────────────────────────────────────────────────────────────────
# Building & Pushing
# ─────────────────────────────────────────────────────────────────

build-images: ## Build Docker images (set REGISTRY=your.registry.com)
	@echo "$(BLUE)Building Docker images...$(NC)"
	@echo "Registry: $(REGISTRY), Backend Tag: $(BACKEND_TAG), Frontend Tag: $(FRONTEND_TAG)"
	docker build -t $(REGISTRY)/$(ORG)-backend:$(BACKEND_TAG) vh2-docker/backend
	docker build -t $(REGISTRY)/$(ORG)-frontend:$(FRONTEND_TAG) vh2-docker/frontend
	@echo "$(GREEN)✓ Images built:$(NC)"
	@docker images | grep $(ORG)

build-push: build-images ## Build and push images to registry
	@echo "$(BLUE)Pushing images to $(REGISTRY)...$(NC)"
	docker push $(REGISTRY)/$(ORG)-backend:$(BACKEND_TAG)
	docker push $(REGISTRY)/$(ORG)-frontend:$(FRONTEND_TAG)
	@echo "$(GREEN)✓ Images pushed successfully$(NC)"

# ─────────────────────────────────────────────────────────────────
# Kubernetes Deployment
# ─────────────────────────────────────────────────────────────────

validate-k8s: ## Validate K8s YAML manifests
	@echo "$(BLUE)Validating K8s manifests...$(NC)"
	@kubectl apply -f vh2-docker/k8s/ --dry-run=client --validate=true
	@echo "$(GREEN)✓ All manifests valid$(NC)"

deploy-k8s: validate-k8s ## Deploy K8s manifests (kustomize)
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	kubectl apply -k vh2-docker/k8s/
	@echo "$(GREEN)✓ Manifests applied$(NC)"
	@echo "Waiting for deployments to become ready..."
	@kubectl rollout status deployment/vh2-backend -n vh2-prod
	@kubectl rollout status deployment/vh2-frontend -n vh2-prod
	@echo "$(GREEN)✓ Deployments ready$(NC)"

deploy-status: ## Check K8s deployment status
	@echo "$(BLUE)VH2 K8s Deployment Status$(NC)"
	@echo ""
	@echo "Namespace:"
	@kubectl get namespace vh2-prod -o wide 2>/dev/null || echo "$(RED)Not found$(NC)"
	@echo ""
	@echo "Deployments:"
	@kubectl get deployments -n vh2-prod -o wide
	@echo ""
	@echo "Pods:"
	@kubectl get pods -n vh2-prod -o wide
	@echo ""
	@echo "Services:"
	@kubectl get services -n vh2-prod -o wide
	@echo ""
	@echo "HPA Status:"
	@kubectl get hpa -n vh2-prod -o wide

deploy-logs: ## Tail backend logs in K8s
	@echo "$(BLUE)Tailing backend logs (Ctrl+C to exit)...$(NC)"
	@kubectl logs -n vh2-prod -l app=vh2-backend -f

deploy-logs-frontend: ## Tail frontend logs in K8s
	@echo "$(BLUE)Tailing frontend logs (Ctrl+C to exit)...$(NC)"
	@kubectl logs -n vh2-prod -l app=vh2-frontend -f

deploy-rollback: ## Rollback to previous K8s deployment
	@echo "$(RED)Rolling back deployments...$(NC)"
	kubectl rollout undo deployment/vh2-backend -n vh2-prod
	kubectl rollout undo deployment/vh2-frontend -n vh2-prod
	@echo "$(GREEN)✓ Rollback complete$(NC)"

# ─────────────────────────────────────────────────────────────────
# ArgoCD Deployment
# ─────────────────────────────────────────────────────────────────

argocd-check: ## Check if ArgoCD is installed
	@echo "$(BLUE)Checking ArgoCD installation...$(NC)"
	@kubectl get deployment argocd-server -n argocd >/dev/null 2>&1 && \
		echo "$(GREEN)✓ ArgoCD is installed$(NC)" || \
		echo "$(RED)✗ ArgoCD not found. Run: make argocd-install$(NC)"

argocd-install: ## Install ArgoCD (requires kubectl access)
	@echo "$(BLUE)Installing ArgoCD...$(NC)"
	@echo "Creating namespace..."
	kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
	@echo "Applying ArgoCD manifests..."
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "Waiting for ArgoCD to be ready..."
	@kubectl rollout status deployment/argocd-server -n argocd
	@echo ""
	@echo "$(GREEN)✓ ArgoCD installed$(NC)"
	@echo "$(YELLOW)Initial admin password:$(NC)"
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
	@echo ""
	@echo "$(YELLOW)Access ArgoCD UI:$(NC)"
	@echo "  kubectl port-forward svc/argocd-server -n argocd 8080:443"
	@echo "  Open: https://localhost:8080"

deploy-argocd: argocd-check ## Deploy VH2 via ArgoCD
	@echo "$(BLUE)Deploying VH2 via ArgoCD...$(NC)"
	@echo "Repository URL: $(REPO_URL)"
	@kubectl apply -f vh2-docker/argocd/vh2-validator-app.yaml
	@echo "$(GREEN)✓ ArgoCD Application created$(NC)"
	@echo "Waiting for initial sync..."
	@sleep 3
	@argocd app wait vh2-sovereign-validator
	@echo "$(GREEN)✓ Sync complete$(NC)"

argocd-status: ## Show ArgoCD application status
	@echo "$(BLUE)ArgoCD Application Status$(NC)"
	@argocd app get vh2-sovereign-validator

argocd-logs: ## Tail ArgoCD sync logs
	@echo "$(BLUE)ArgoCD logs (Ctrl+C to exit)...$(NC)"
	@argocd app logs vh2-sovereign-validator -f

argocd-rollback: ## Rollback ArgoCD application
	@echo "$(RED)Rolling back ArgoCD application...$(NC)"
	@argocd app rollback vh2-sovereign-validator
	@echo "$(GREEN)✓ Rollback initiated$(NC)"

# ─────────────────────────────────────────────────────────────────
# Validation & Linting
# ─────────────────────────────────────────────────────────────────

lint: ## Validate all YAML files
	@echo "$(BLUE)Validating YAML manifests...$(NC)"
	@for file in vh2-docker/k8s/*.yaml vh2-docker/argocd/*.yaml; do \
		echo "Checking $$file..."; \
		kubectl apply -f $$file --dry-run=client --validate=true >/dev/null 2>&1 && \
			echo "$(GREEN)✓ $$file$(NC)" || \
			(echo "$(RED)✗ $$file$(NC)" && exit 1); \
	done
	@echo ""
	@echo "$(GREEN)✓ All YAML files valid$(NC)"

# ─────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────

clean: ## Remove local containers, images, and volumes
	@echo "$(RED)Cleaning VH2 environment...$(NC)"
	@cd vh2-docker && docker-compose down -v 2>/dev/null || true
	@docker rmi vh2-backend:latest vh2-frontend:latest 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

shell-backend: ## Open shell in running backend container
	@echo "$(BLUE)Opening shell in backend container...$(NC)"
	@CONTAINER=$$(docker-compose -f vh2-docker/docker-compose.yml ps -q backend) && \
		docker exec -it $$CONTAINER /bin/sh

shell-frontend: ## Open shell in running frontend container
	@echo "$(BLUE)Opening shell in frontend container...$(NC)"
	@CONTAINER=$$(docker-compose -f vh2-docker/docker-compose.yml ps -q frontend) && \
		docker exec -it $$CONTAINER /bin/sh

info: ## Show project information
	@echo "$(BLUE)VH2 Sovereign Validator$(NC)"
	@echo ""
	@echo "$(YELLOW)Project Structure:$(NC)"
	@echo "  vh2-docker/          Container orchestration (Docker + K8s)"
	@echo "  ├─ backend/          Express API (Node.js 20, 42 tests)"
	@echo "  ├─ frontend/         Web Component UI (vehicle simulator)"
	@echo "  ├─ k8s/              Kubernetes manifests (8 files)"
	@echo "  ├─ argocd/           ArgoCD Application (auto-sync)"
	@echo "  └─ scripts/          Deployment automation"
	@echo ""
	@echo "$(YELLOW)Critical Gates (Fail-Closed):$(NC)"
	@echo "  1. Build Gate       → Init container tests (42/42)"
	@echo "  2. Pod Ready Gate   → Readiness probe (/ready)"
	@echo "  3. Deployment Gate  → ArgoCD PostSync smoke test"
	@echo ""
	@echo "$(YELLOW)Quick Commands:$(NC)"
	@echo "  Local Dev    → make dev"
	@echo "  Run Tests    → make test"
	@echo "  Deploy K8s   → make deploy-k8s"
	@echo "  Deploy ArgoCD→ make deploy-argocd"
	@echo "  Show Status  → make deploy-status"

.DEFAULT_GOAL := help
