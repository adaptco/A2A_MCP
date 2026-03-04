from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineContext:
    run_id: str
    staging_root: Path = field(default_factory=lambda: Path("staging"))
    export_root: Path = field(default_factory=lambda: Path("exports"))
