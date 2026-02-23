from __future__ import annotations
from dataclasses import dataclass

@dataclass
class MergeModel:
    @classmethod
    def from_file(cls, path: str) -> MergeModel:
        return cls()

    @classmethod
    def empty(cls) -> MergeModel:
        return cls()
