#!/usr/bin/env python3
"""
Deployment Bot Microservice Agent

Responsibilities:
- Build VH2 system Docker images
- Deploy full stack via docker-compose
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
from typing import Optional, Dict, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/deployment_bot.log", mode="a")
    ]
)
logger = logging.getLogger("DeploymentBot")

# Configuration
COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose.prod.yaml")
PROJECT_NAME = os.getenv("PROJECT_NAME", "vh2-stack")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
RECOVERY_ATTEMPTS = int(os.getenv("RECOVERY_ATTEMPTS", "3"))
RECOVERY_DELAY = int(os.getenv("RECOVERY_DELAY", "10"))
LOG_DIR = Path("/var/log/deployment_bot")


class DeploymentBot:
    """Microservice agent for orchestrating deployment, monitoring, and recovery."""

    def __init__(self, compose_file: str = COMPOSE_FILE, project_name: str = PROJECT_NAME):
        self.compose_file = compose_file
        self.project_name = project_name
        self.log_dir = LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DeploymentBot initialized | compose={compose_file} | project={project_name}")

    def run_command(self, cmd: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        """Execute shell command and return exit code, stdout, stderr."""
        logger.debug(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            return 124, "", str(e)
        except Exception as e:
            logger.error(f"Command failed: {' '.join(cmd)} | Error: {e}")
            return 1, "", str(e)

    def build_images(self) -> bool:
        """Build all Docker images defined in compose file."""
        logger.info("Starting image build...")
        cmd = ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "build", "--no-cache"]
        returncode, stdout, stderr = self.run_command(cmd, timeout=600)

        if returncode == 0:
            logger.info("✓ Image build completed successfully")
            self._log_output("build.log", stdout)
            return True
        else:
            logger.error(f"✗ Image build failed | {stderr}")
            self._log_output("build_error.log", stderr)
            return False

    def deploy_stack(self) -> bool:
        """Deploy full stack using docker-compose."""
        logger.info("Starting stack deployment...")
        cmd = [
            "docker-compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "up", "-d"
        ]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode == 0:
            logger.info("✓ Stack deployed successfully")
            self._log_output("deploy.log", stdout)
            time.sleep(5)  # Give services time to stabilize
            return True
        else:
            logger.error(f"✗ Stack deployment failed | {stderr}")
            self._log_output("deploy_error.log", stderr)
            return False

    def get_container_status(self) -> Dict[str, Dict]:
        """Get status of all containers in project."""
        cmd = [
            "docker-compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            "ps", "--format", "json"
        ]
        returncode, stdout, stderr = self.run_command(cmd)

        if returncode != 0:
            logger.error(f"Failed to get container status: {stderr}")
            return {}

        try:
            containers = json.loads(stdout)
            status_dict = {}
            for container in containers:
                name = container.get("Service", "unknown")
                state = container.get("State", "unknown")
                status_dict[name] = {
                    "state": state,
                    "status": container.get("Status", ""),
                    "id": container.get("ID", ""),
                }
            return status_dict
        except json.JSONDecodeError:
            logger.error("Failed to parse container status JSON")
            return {}

    def check_health(self) -> Dict[str, bool]:
        """Check health of all services."""
        status = self.get_container_status()
        health = {}

        for service_name, info in status.items():
            state = info.get("state", "").lower()
            is_healthy = state in ["running", "up"]
            health[service_name] = is_healthy
            logger.info(f"Service '{service_name}': {info.get('status')} [{'✓' if is_healthy else '✗'}]")

        return health

    def recover_service(self, service_name: str) -> bool:
        """Attempt to recover a failed service."""
        logger.warning(f"Attempting recovery for service: {service_name}")

        for attempt in range(1, RECOVERY_ATTEMPTS + 1):
            logger.info(f"Recovery attempt {attempt}/{RECOVERY_ATTEMPTS}")

            # Restart the service
            cmd = [
                "docker-compose",
                "-f", self.compose_file,
                "-p", self.project_name,
                "restart", service_name
            ]
            returncode, stdout, stderr = self.run_command(cmd, timeout=60)

            if returncode == 0:
                logger.info(f"✓ Service '{service_name}' restarted successfully")
                time.sleep(RECOVERY_DELAY)

                # Verify it's running
                status = self.get_container_status()
                if service_name in status:
                    state = status[service_name].get("state", "").lower()
                    if state in ["running", "up"]:
                        logger.info(f"✓ Service '{service_name}' is healthy")
                        return True

            time.sleep(RECOVERY_DELAY)

        logger.error(f"✗ Failed to recover service '{service_name}' after {RECOVERY_ATTEMPTS} attempts")
        return False

    def monitor_loop(self, interval: int = HEALTH_CHECK_INTERVAL):
        """Continuous monitoring loop."""
        logger.info(f"Starting monitoring loop (interval={interval}s)")

        try:
            while True:
                health = self.check_health()
                unhealthy = [svc for svc, is_healthy in health.items() if not is_healthy]

                if unhealthy:
                    logger.warning(f"Unhealthy services detected: {unhealthy}")
                    for service in unhealthy:
                        self.recover_service(service)
                else:
                    logger.info("All services healthy")

                self._log_health_snapshot(health)
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}", exc_info=True)

    def _log_output(self, filename: str, content: str):
        """Log command output to file."""
        try:
            log_file = self.log_dir / filename
            with open(log_file, "a") as f:
                f.write(f"\n--- {datetime.now().isoformat()} ---\n")
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write log file: {e}")

    def _log_health_snapshot(self, health: Dict[str, bool]):
        """Log health snapshot to file."""
        try:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "health": health,
                "all_healthy": all(health.values())
            }
            health_log = self.log_dir / "health_snapshots.jsonl"
            with open(health_log, "a") as f:
                f.write(json.dumps(snapshot) + "\n")
        except Exception as e:
            logger.error(f"Failed to log health snapshot: {e}")

    def show_status(self):
        """Display current status of all containers."""
        logger.info("=== DEPLOYMENT STATUS ===")
        status = self.get_container_status()
        health = self.check_health()

        for service_name, info in status.items():
            is_healthy = health.get(service_name, False)
            health_badge = "✓" if is_healthy else "✗"
            print(f"{health_badge} {service_name:20} | {info.get('status')}")

        logger.info("=== END STATUS ===")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="VH2 Deployment Bot Microservice")
    parser.add_argument(
        "action",
        choices=["build", "deploy", "monitor", "status", "recover", "full-deploy"],
        help="Action to perform"
    )
    parser.add_argument(
        "--service",
        default=None,
        help="Service name for recover action"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=HEALTH_CHECK_INTERVAL,
        help="Health check interval in seconds"
    )
    parser.add_argument(
        "--compose-file",
        default=COMPOSE_FILE,
        help="Path to docker-compose file"
    )

    args = parser.parse_args()

    bot = DeploymentBot(compose_file=args.compose_file)

    if args.action == "build":
        success = bot.build_images()
        sys.exit(0 if success else 1)

    elif args.action == "deploy":
        success = bot.deploy_stack()
        sys.exit(0 if success else 1)

    elif args.action == "monitor":
        bot.monitor_loop(interval=args.interval)

    elif args.action == "status":
        bot.show_status()

    elif args.action == "recover":
        if not args.service:
            logger.error("--service required for recover action")
            sys.exit(1)
        success = bot.recover_service(args.service)
        sys.exit(0 if success else 1)

    elif args.action == "full-deploy":
        logger.info("Starting full deployment pipeline...")
        if bot.build_images() and bot.deploy_stack():
            logger.info("Full deployment succeeded. Starting monitoring...")
            bot.show_status()
            bot.monitor_loop(interval=args.interval)
        else:
            logger.error("Full deployment failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
