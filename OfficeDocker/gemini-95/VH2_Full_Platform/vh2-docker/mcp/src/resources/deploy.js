/**
 * VH2 MCP Resource — vh2://deploy
 *
 * Provides a structured summary of the full deployment topology:
 * Docker sockets, Kubernetes manifests, ArgoCD GitOps config.
 * Useful for CI agents and IDE assistants reasoning about the infra.
 */

export const deployResource = {
  uri:         'vh2://deploy',
  name:        'VH2 Deployment Topology',
  description: 'Docker + Kubernetes + ArgoCD deployment manifest summary. Lists all services, ports, health endpoints, image tags, and GitOps sync policy. Read this for infrastructure context before modifying deployment configs.',
  mimeType:    'application/json',

  async read() {
    return {
      contents: [{
        uri:      'vh2://deploy',
        mimeType: 'application/json',
        text: JSON.stringify({
          docker: {
            services: {
              backend: {
                image:     'vh2-backend:1.0.0',
                port:      3001,
                network:   'vh2-internal (not public)',
                health:    'GET http://localhost:3001/health',
                test_gate: 'node tests/validator.test.js (42 tests, fail-closed)',
                endpoints: [
                  'GET  /health',
                  'GET  /api/spec',
                  'POST /api/validate',
                  'POST /api/witness',
                  'GET  /api/ackermann/:deg',
                  'GET  /api/kpi',
                ],
              },
              frontend: {
                image:  'vh2-frontend:1.0.0',
                port:   3000,
                assets: ['/', '/vehicle.html', '/tests.html', '/vh2-plugin.js'],
              },
              nginx: {
                image: 'nginx:1.25-alpine',
                port:  80,
                routes: {
                  '/api/*':  'backend:3001',
                  '/health': 'backend:3001',
                  '/*':      'frontend:3000',
                },
              },
            },
            compose_files: ['docker-compose.yml', 'docker-compose.prod.yml'],
          },
          kubernetes: {
            namespace:  'vh2-prod',
            manifests: [
              'k8s/namespace.yaml         — vh2-prod + ResourceQuota',
              'k8s/configmap-spec.yaml    — canonical spec as ConfigMap',
              'k8s/backend-deployment.yaml— Deployment + Service + HPA (3–10 pods)',
              'k8s/frontend-deployment.yaml—Deployment + Service + HPA (2–5 pods)',
              'k8s/ingress.yaml           — TLS ingress, /api/* → backend',
              'k8s/network-policy.yaml    — zero-trust (4 NetworkPolicy objects)',
              'k8s/tests-job.yaml         — PostSync smoke test Job',
              'k8s/kustomization.yaml     — Kustomize composition',
            ],
            init_container: {
              name:    'validator-gate',
              command: 'node tests/validator.test.js',
              effect:  'Blocks pod startup if any of 42 tests fail',
            },
            hpa: {
              backend:  { min: 3, max: 10, cpu_target: '70%' },
              frontend: { min: 2, max: 5,  cpu_target: '75%' },
            },
          },
          argocd: {
            app:            'vh2-sovereign-validator',
            source_path:    'k8s/',
            target_revision:'main',
            sync_policy:    'automated (prune=true, selfHeal=true)',
            post_sync_hook: 'vh2-smoke-test Job (curl-based, 6 checks)',
            rollback:       'argocd app rollback vh2-sovereign-validator',
          },
          mcp: {
            transport: 'StdioServerTransport',
            tools:     ['vh2_validate', 'vh2_ackermann', 'vh2_kpi', 'vh2_witness'],
            resources: ['vh2://spec', 'vh2://invariants', 'vh2://deploy'],
            protocol:  'JSON-RPC 2.0 over stdin/stdout',
            version:   '2024-11-05',
          },
        }, null, 2),
      }],
    }
  },
}
