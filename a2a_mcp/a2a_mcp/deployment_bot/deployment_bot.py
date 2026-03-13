#!/usr/bin/env python3
"""
Deployment Bot Microservice Agent — A2A_MCP Digital Twin Edition

Responsibilities:
- Build Digital Twin Docker images
- Deploy full twin stack via docker-compose
- Monitor health checks and container status
- Auto-recover by restarting unhealthy services
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose.twin.yml")
PROJECT_NAME = os.getenv("PROJECT_NAME", "a2a-twin")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
RECOVERY_ATTEMPTS = int(os.getenv("RECOVERY_ATTEMPTS", "3"))
RECOVERY_DELAY = int(os.getenv("RECOVERY_DELAY", "10"))

# Cross-platform log directory (relative, works on Windows & Linux)
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs/deployment_bot"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "deployment_bot.log", mode="a"),
    ],
)
logger = logging.getLogger("DeploymentBot")


# ---------------------------------------------------------------------------
# Bot class
# ---------------------------------------------------------------------------

class DeploymentBot:
    """Microservice agent for orchestrating twin deployment, monitoring, and recovery."""

    def __init__(self, compose_file: str = COMPOSE_FILE, project_name: str = PROJECT_NAME):
        self.compose_file = compose_file
        self.project_name = project_name
        self.log_dir = LOG_DIR
        logger.info(
            "DeploymentBot initialised | compose=%s | project=%s",
            compose_file,
            project_name,
        )

    def run_command(self, cmd: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        """Execute shell command and return (exit_code, stdout, stderr)."""
        logger.debug("Running: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            logger.error("Command timeout: %s", " ".join(cmd))
            return 124, "", str(e)
        except Exception as e:
            logger.error("Command failed: %s | Error: %s", " ".join(cmd), e)
            return 1, "", str(e)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_images(self) -> bool:
        """Build all Docker images defined in compose file."""
        logger.info("Starting image build…")
        cmd = [
            "docker", "compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "build", "--no-cache",
        ]
        returncode, stdout, stderr = self.run_command(cmd, timeout=600)
        if returncode == 0:
            logger.info("✓ Image build completed")
            self._log_output("build.log", stdout)
            return True
        logger.error("✗ Image build failed | %s", stderr)
        self._log_output("build_error.log", stderr)
        return False

    # ------------------------------------------------------------------
    # Deploy
    # ------------------------------------------------------------------

    def deploy_stack(self) -> bool:
        """Deploy full twin stack."""
        logger.info("Starting stack deployment…")
        cmd = [
            "docker", "compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "up", "-d",
        ]
        returncode, stdout, stderr = self.run_command(cmd)
        if returncode == 0:
            logger.info("✓ Stack deployed successfully")
            self._log_output("deploy.log", stdout)
            time.sleep(5)  # Allow services to stabilise
            return True
        logger.error("✗ Stack deployment failed | %s", stderr)
        self._log_output("deploy_error.log", stderr)
        return False

    # ------------------------------------------------------------------
    # Status & Health
    # ------------------------------------------------------------------

    def get_container_status(self) -> Dict[str, Dict]:
        """Query container status for all services in the project."""
        cmd = [
            "docker", "compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "ps", "--format", "json",
        ]
        returncode, stdout, stderr = self.run_command(cmd)
        if returncode != 0:
            logger.error("Failed to get container status: %s", stderr)
            return {}

        status_dict: Dict[str, Dict] = {}
        try:
            # docker compose ps --format json emits one JSON object per line
            for line in stdout.strip().splitlines():
                if not line.strip():
                    continue
                container = json.loads(line)
                name = container.get("Service", "unknown")
                status_dict[name] = {
                    "state": container.get("State", "unknown"),
                    "status": container.get("Status", ""),
                    "id": container.get("ID", ""),
                }
        except json.JSONDecodeError:
            logger.error("Failed to parse container status JSON")
        return status_dict

    def check_health(self) -> Dict[str, bool]:
        """Return health for every running service."""
        status = self.get_container_status()
        health: Dict[str, bool] = {}
        for service_name, info in status.items():
            state = info.get("state", "").lower()
            is_healthy = state in ("running", "up")
            health[service_name] = is_healthy
            badge = "✓" if is_healthy else "✗"
            logger.info("Service '%s': %s [%s]", service_name, info.get("status"), badge)
        return health

    def show_status(self):
        """Print a formatted status table."""
        logger.info("=== DEPLOYMENT STATUS ===")
        status = self.get_container_status()
        health = self.check_health()
        for service_name, info in status.items():
            badge = "✓" if health.get(service_name) else "✗"
            print(f"{badge} {service_name:25} | {info.get('status')}")
        logger.info("=== END STATUS ===")

    # ------------------------------------------------------------------
    # Recovery
    # ------------------------------------------------------------------

    def recover_service(self, service_name: str) -> bool:
        """Attempt to restart an unhealthy service with retry logic."""
        logger.warning("Attempting recovery for service: %s", service_name)
        for attempt in range(1, RECOVERY_ATTEMPTS + 1):
            logger.info("Recovery attempt %d/%d", attempt, RECOVERY_ATTEMPTS)
            cmd = [
                "docker", "compose",
                "-f", self.compose_file,
                "-p", self.project_name,
                "restart", service_name,
            ]
            returncode, _, stderr = self.run_command(cmd, timeout=60)
            if returncode == 0:
                time.sleep(RECOVERY_DELAY)
                status = self.get_container_status()
                if status.get(service_name, {}).get("state", "").lower() in ("running", "up"):
                    logger.info("✓ Service '%s' recovered", service_name)
                    return True
            else:
                logger.warning("Restart failed: %s", stderr)
            time.sleep(RECOVERY_DELAY)
        logger.error("✗ Could not recover service '%s' after %d attempts", service_name, RECOVERY_ATTEMPTS)
        return False

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def monitor_loop(self, interval: int = HEALTH_CHECK_INTERVAL):
        """Continuous health + recovery loop."""
        logger.info("Starting monitoring loop (interval=%ds)", interval)
        try:
            while True:
                health = self.check_health()
                unhealthy = [svc for svc, ok in health.items() if not ok]
                if unhealthy:
                    logger.warning("Unhealthy services: %s", unhealthy)
                    for svc in unhealthy:
                        self.recover_service(svc)
                else:
                    logger.info("All twin services healthy ✓")
                self._log_health_snapshot(health)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error("Monitoring loop error: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_output(self, filename: str, content: str):
        try:
            log_file = self.log_dir / filename
            with open(log_file, "a") as f:
                f.write(f"\n--- {datetime.now().isoformat()} ---\n{content}")
        except Exception as e:
            logger.error("Failed to write log file: %s", e)

    def _log_health_snapshot(self, health: Dict[str, bool]):
        try:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "health": health,
                "all_healthy": all(health.values()) if health else False,
            }
            health_log = self.log_dir / "health_snapshots.jsonl"
            with open(health_log, "a") as f:
                f.write(json.dumps(snapshot) + "\n")
        except Exception as e:
            logger.error("Failed to log health snapshot: %s", e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="A2A_MCP Digital Twin Deployment Bot")
    parser.add_argument(
        "action",
        choices=["build", "deploy", "monitor", "status", "recover", "full-deploy"],
        help="Action to perform",
    )
    parser.add_argument("--service", default=None, help="Service name for recover action")
    parser.add_argument("--interval", type=int, default=HEALTH_CHECK_INTERVAL, help="Health check interval (s)")
    parser.add_argument("--compose-file", default=COMPOSE_FILE, help="Path to docker-compose file")
    parser.add_argument("--project", default=PROJECT_NAME, help="Docker Compose project name")

    args = parser.parse_args()
    bot = DeploymentBot(compose_file=args.compose_file, project_name=args.project)

    actions = {
        "build": lambda: sys.exit(0 if bot.build_images() else 1),
        "deploy": lambda: sys.exit(0 if bot.deploy_stack() else 1),
        "monitor": lambda: bot.monitor_loop(interval=args.interval),
        "status": lambda: bot.show_status(),
        "recover": lambda: (
            (logger.error("--service required for recover"), sys.exit(1))
            if not args.service
            else sys.exit(0 if bot.recover_service(args.service) else 1)
        ),
        "full-deploy": lambda: (
            (
                logger.info("Full deployment pipeline…"),
                bot.build_images() and bot.deploy_stack() and (
                    bot.show_status() or True
                ) and bot.monitor_loop(interval=args.interval)
            )
            or (logger.error("Full deployment failed"), sys.exit(1))
        ),
    }

    actions[args.action]()


if __name__ == "__main__":
    main()
