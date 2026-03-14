from __future__ import annotations

import abc
from typing import Dict, Optional

import numpy as np


class BaselineStore(abc.ABC):
    """
    Abstract base class for persisting drift baselines.
    Implementations can store baselines in memory, local files (Parquet), or cloud storage (S3/Redis).
    """

    @abc.abstractmethod
    async def load(self, feature_name: str) -> Optional[np.ndarray]:
        """
        Load a baseline for a given feature.
        Returns None if no baseline exists.
        """
        pass

    @abc.abstractmethod
    async def save(self, feature_name: str, baseline: np.ndarray) -> None:
        """
        Save a baseline for a given feature.
        """
        pass


class InMemoryBaselineStore(BaselineStore):
    """
    Simple in-memory store for testing and development.
    Not persistent across process restarts.
    """

    def __init__(self) -> None:
        self._store: Dict[str, np.ndarray] = {}

    async def load(self, feature_name: str) -> Optional[np.ndarray]:
        return self._store.get(feature_name)

    async def save(self, feature_name: str, baseline: np.ndarray) -> None:
        # Store a copy to prevent external modification affecting the store
        self._store[feature_name] = np.array(baseline, copy=True)
