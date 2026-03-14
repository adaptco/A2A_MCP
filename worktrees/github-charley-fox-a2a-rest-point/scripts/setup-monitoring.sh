#!/bin/bash
# Health check and monitoring setup script
# Configures health endpoints and monitoring for the application

set -e

echo "🏥 Setting up health checks and monitoring..."

# ============================================================================
# Application Health Endpoints
# ============================================================================
echo ""
echo "📋 Application should implement these health check endpoints:"
echo ""
echo "GET /health"
echo "  Returns: 200 OK"
echo "  Response:"
echo '  {'
echo '    "status": "ok",'
echo '    "timestamp": "2026-01-01T00:00:00Z",'
echo '    "version": "1.0.0"'
echo '  }'
echo ""
echo "GET /ready"
echo "  Returns: 200 OK when all dependencies are ready"
echo "  Returns: 503 if any critical dependency is down"
echo "  Response:"
echo '  {'
echo '    "ready": true,'
echo '    "dependencies": {'
echo '      "database": "connected",'
echo '      "redis": "connected"'
echo '    }'
echo '  }'
echo ""
echo "GET /metrics"
echo "  Returns Prometheus metrics in text format"
echo "  Scrape interval: 30s (configurable in ServiceMonitor)"
echo ""

# ============================================================================
# Kubernetes Probes Configuration
# ============================================================================
echo ""
echo "🔍 Kubernetes Probes already configured in deployment manifests:"
echo ""
echo "  • Startup Probe: Gives app 150 seconds to start (5 retries × 30s)"
echo "  • Liveness Probe: Checks /health every 10 seconds, restarts after 3 failures"
echo "  • Readiness Probe: Checks /ready every 5 seconds, removes from traffic after 2 failures"
echo ""

# ============================================================================
# Logging Configuration
# ============================================================================
echo ""
echo "📝 Logging recommendations:"
echo ""
echo "  • Use structured JSON logging (Winston, Pino, Bunyan)"
echo "  • Log levels: error, warn, info, debug, trace"
echo "  • Include in every log:"
echo "    - timestamp"
echo "    - level"
echo "    - message"
echo "    - request ID (X-Request-ID)"
echo "    - user ID (if applicable)"
echo "    - stack trace (for errors)"
echo ""
echo "  • Log format example:"
echo '    {"timestamp":"2026-01-01T00:00:00.000Z","level":"info","message":"Request received","requestId":"abc-123","userId":"user-456"}'
echo ""

# ============================================================================
# Metrics Configuration
# ============================================================================
echo ""
echo "📊 Key metrics to expose (Prometheus format):"
echo ""
echo "  • http_requests_total (counter)"
echo "    - Labels: method, path, status, service"
echo ""
echo "  • http_request_duration_seconds (histogram)"
echo "    - Labels: method, path, status"
echo ""
echo "  • database_connection_pool_size (gauge)"
echo "  • database_queries_total (counter)"
echo "  • redis_commands_total (counter)"
echo ""

# ============================================================================
# Alert Configuration
# ============================================================================
echo ""
echo "🚨 Alerts configured in monitoring.yaml:"
echo ""
echo "  • PodRestartingTooOften: > 0.1 restarts/min for 5 min"
echo "  • HighCPUUsage: > 80% CPU for 5 min"
echo "  • HighMemoryUsage: > 80% memory for 5 min"
echo "  • DeploymentNotReady: Unavailable replicas present for 5 min"
echo "  • HighErrorRate: > 5% 5xx errors for 5 min"
echo ""

# ============================================================================
# Deployment
# ============================================================================
echo ""
echo "🚀 To deploy monitoring:"
echo ""
echo "  1. Install Prometheus Operator (if not already installed):"
echo "     helm repo add prometheus-community https://prometheus-community.github.io/helm-charts"
echo "     helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace"
echo ""
echo "  2. Deploy monitoring configuration:"
echo "     kubectl apply -f k8s/production/monitoring.yaml"
echo ""
echo "  3. Access Prometheus dashboard:"
echo "     kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090"
echo "     Visit http://localhost:9090"
echo ""
echo "  4. Access Grafana dashboard:"
echo "     kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
echo "     Visit http://localhost:3000 (default: admin/prom-operator)"
echo ""

# ============================================================================
# Implementation Guide
# ============================================================================
echo ""
echo "📖 Implementation guide:"
cat << 'EOF'

1. Add health endpoints to your Express app:

   import express from 'express';
   
   const app = express();
   
   // Health check - basic readiness
   app.get('/health', (req, res) => {
     res.json({
       status: 'ok',
       timestamp: new Date().toISOString(),
       version: '1.0.0'
     });
   });
   
   // Readiness check - all dependencies ready?
   app.get('/ready', async (req, res) => {
     try {
       // Check database
       await db.query('SELECT 1');
       // Check Redis
       await redis.ping();
       
       res.json({
         ready: true,
         dependencies: {
           database: 'connected',
           redis: 'connected'
         }
       });
     } catch (err) {
       res.status(503).json({
         ready: false,
         error: err.message
       });
     }
   });
   
   // Metrics endpoint (install prom-client)
   import promClient from 'prom-client';
   
   app.get('/metrics', async (req, res) => {
     res.set('Content-Type', promClient.register.contentType);
     res.end(await promClient.register.metrics());
   });

2. Add Prometheus client initialization:

   import promClient from 'prom-client';
   
   // Create metrics
   const httpRequestDuration = new promClient.Histogram({
     name: 'http_request_duration_seconds',
     help: 'Duration of HTTP requests in seconds',
     labelNames: ['method', 'path', 'status'],
     buckets: [0.1, 0.5, 1, 2, 5]
   });
   
   const httpRequestTotal = new promClient.Counter({
     name: 'http_requests_total',
     help: 'Total HTTP requests',
     labelNames: ['method', 'path', 'status']
   });
   
   // Middleware to track requests
   app.use((req, res, next) => {
     const start = Date.now();
     res.on('finish', () => {
       const duration = (Date.now() - start) / 1000;
       httpRequestDuration
         .labels(req.method, req.path, res.statusCode)
         .observe(duration);
       httpRequestTotal
         .labels(req.method, req.path, res.statusCode)
         .inc();
     });
     next();
   });

EOF

echo ""
echo "✅ Health check and monitoring setup guide complete!"
echo ""
