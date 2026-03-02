"""Configuration helpers for the CODEX qernel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional


@dataclass(frozen=True)
class QernelConfig:
    """Runtime configuration describing the AxQxOS CODEX qernel environment."""

    os_name: str = "AxQxOS"
    qernel_version: str = "1.0.0"
    capsules_dir: Path = Path("capsules")
    events_log: Path = Path("var/log/codex_qernel_events.ndjson")
    scrollstream_ledger: Path = Path("var/log/scrollstream_ledger.ndjson")
    auto_refresh: bool = True

    @classmethod
    def from_env(cls, *, base_dir: Optional[Path] = None) -> "QernelConfig":
        """Create a configuration instance derived from environment variables."""

        def _path_from_env(var: str, default: Path) -> Path:
            value = os.getenv(var)
            if not value:
                return default
            candidate = Path(value)
            if not candidate.is_absolute() and base_dir is not None:
                candidate = base_dir / candidate
            return candidate

        base = base_dir or Path.cwd()
        os_name = os.getenv("AXQXOS_NAME", "AxQxOS")
        qernel_version = os.getenv("CODEX_QERNEL_VERSION", "1.0.0")
        capsules_dir = _path_from_env("CODEX_CAPSULE_DIR", base / "capsules")
        events_log = _path_from_env("CODEX_EVENTS_LOG", base / "var/log/codex_qernel_events.ndjson")
        scrollstream_ledger = _path_from_env(
            "CODEX_SCROLLSTREAM_LEDGER", base / "var/log/scrollstream_ledger.ndjson"
        )
        auto_refresh_env = os.getenv("CODEX_AUTO_REFRESH", "1").lower()
        auto_refresh = auto_refresh_env not in {"0", "false", "no"}
        return cls(
            os_name=os_name,
            qernel_version=qernel_version,
            capsules_dir=capsules_dir,
            events_log=events_log,
            auto_refresh=auto_refresh,
            scrollstream_ledger=scrollstream_ledger,
        )

    def ensure_directories(self) -> None:
        """Ensure that the capsule and log directories exist."""

        self.capsules_dir.mkdir(parents=True, exist_ok=True)
        self.events_log.parent.mkdir(parents=True, exist_ok=True)
        self.scrollstream_ledger.parent.mkdir(parents=True, exist_ok=True)
