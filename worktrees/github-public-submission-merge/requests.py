from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class _Response:
    status_code: int = 200
    _payload: Dict[str, Any] | None = None

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Dict[str, Any]:
        return self._payload or {"choices": [{"message": {"content": "# simulated completion"}}]}


def post(url: str, headers: Dict[str, str] | None = None, json: Dict[str, Any] | None = None, **kwargs: Any) -> _Response:
    return _Response()
