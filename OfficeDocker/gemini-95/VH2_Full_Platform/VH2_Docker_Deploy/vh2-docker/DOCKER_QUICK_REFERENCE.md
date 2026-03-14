# VH2 Docker Compose — Quick Reference

## One-Line Start

```bash
# Development (with rebuild)
docker compose up --build

# Production
ALLOWED_ORIGIN=https://yourdomain.com docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Service Health

```bash
# Check all services
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs (single service)
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
```

## Testing

```bash
# Backend tests run during build (fail-closed)
docker compose build backend

# Manual API test
curl http://localhost/api/health
curl http://localhost/api/spec

# Validate endpoint
curl -X POST http://localhost/api/validate \
  -H 'Content-Type: application/json' \
  -d '{"spoke_count":5,"rim_diameter_in":19,"front_et_mm":29,"rear_et_mm":22}'
```

## Debugging

```bash
# Shell into backend
docker compose exec backend sh

# Shell into frontend
docker compose exec frontend sh

# Inspect container network
docker network inspect vh2-docker_vh2-internal
docker network inspect vh2-docker_vh2-public

# View container processes
docker compose top backend
docker compose top frontend
docker compose top nginx
```

## Cleanup

```bash
# Stop services (keep volumes)
docker compose down

# Remove images too
docker compose down --rmi all

# Remove dangling images and volumes
docker system prune -a --volumes
```

## Environment Variables

Production override uses `$ALLOWED_ORIGIN` for CORS:

```bash
export ALLOWED_ORIGIN=https://yourdomain.com
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Or inline:

```bash
ALLOWED_ORIGIN=https://yourdomain.com \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Image Inspection

```bash
# List built images
docker images | grep vh2

# Inspect backend image
docker inspect vh2-docker-backend

# View Dockerfile history
docker history vh2-docker-backend

# Check image size
docker images vh2-docker-backend --format "table {{.Repository}}\t{{.Size}}"
```

## Build Details

Both services use multi-stage builds:

- **Stage 1**: `deps` — Installs production dependencies only
- **Stage 2**: `test` (backend only) — Runs tests; build fails if tests fail
- **Stage 3**: `production` — Minimal runtime image

Build times:
- Backend: ~30s (first build), ~3s (cached)
- Frontend: ~15s (first build), ~3s (cached)

## Network Isolation

```
vh2-internal (internal: true) ← Backend, Frontend (isolated from outside)
    ↓
vh2-public (bridge)          ← Nginx exposes port 80 only
```

Backend and Frontend are never exposed directly; all traffic routes through nginx.

## Health Checks

All services implement health checks compatible with Docker Compose and Kubernetes:

| Service | Check | Interval | Start Period |
|---------|-------|----------|--------------|
| backend | GET /health | 20s | 10s |
| frontend | GET / | 20s | 8s |
| nginx | nginx -t | 30s | - |

Services wait for each other:
- nginx waits for backend AND frontend to be healthy before starting
- compose respects `depends_on.condition: service_healthy`

## Resource Limits (Production)

Edit `docker-compose.prod.yml` to adjust limits:

```yaml
backend:
  deploy:
    resources:
      limits:       { cpus: '0.50', memory: '256M' }
      reservations: { cpus: '0.10', memory: '64M' }
```

Check actual usage:

```bash
docker stats vh2-backend vh2-frontend vh2-nginx
```

## Logging

All services use json-file driver with rotation:

```bash
# View real-time logs
docker compose logs -f

# View last 100 lines
docker compose logs --tail 100

# Follow from specific service
docker compose logs -f backend
```

Log files stored in:
- `/var/lib/docker/containers/<container-id>/`
- Max: 10MB per file, 3 files total
- Automatically rotated

## Port Mapping

| Service | Internal Port | Public Port | Network |
|---------|---------------|-------------|---------|
| backend | 3001 | (none) | vh2-internal |
| frontend | 3000 | (none) | vh2-internal |
| nginx | 80 | 80 (HTTP) | vh2-public |

For production HTTPS, add to `docker-compose.prod.yml`:

```yaml
nginx:
  ports:
    - "80:80"
    - "443:443"
```

And configure TLS in `nginx/nginx.conf`.

## Security

- ✓ All services run as non-root user `vh2` (uid:1001)
- ✓ Read-only filesystem (except `/tmp` tmpfs)
- ✓ No privileged escalation (`no-new-privileges:true`)
- ✓ Backend isolated on internal network
- ✓ Nginx is the only public-facing service
- ✓ Security headers configured in nginx.conf

## Next Steps

1. **CI/CD**: Set up GitHub Actions or Docker Build Cloud
2. **Registry**: Push to Docker Hub or private registry
3. **Kubernetes**: Images are ready for K8s deployment (health checks compatible)
4. **Monitoring**: Use Docker Scout for image scanning
5. **TLS**: Enable HTTPS in production (nginx.conf template ready)

---

For full details, see `CONTAINERIZATION_SUMMARY.md`.
