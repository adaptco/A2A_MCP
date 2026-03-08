# Plan ingress scheduler snippets

This folder stores application-level scheduler code snippets that invoke the orchestrator's `plan_ingress` handler.

- `ingress.py` contains the FastAPI startup hook example for registering a daily ingress job (`daily-game-design-run`).
- The GitHub Actions workflow `.github/workflows/daily_ingress.yml` triggers ingress via HTTP on a cron schedule; this script is for in-app scheduler wiring when running inside the application process.
