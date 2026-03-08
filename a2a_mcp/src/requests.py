from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class RequestException(Exception):
    """Compatibility exception matching the requests API surface."""


class _Exceptions:
    RequestException = RequestException


exceptions = _Exceptions()


@dataclass
class _Response:
    status_code: int = 200
    _payload: Dict[str, Any] | None = None
    text: str = ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RequestException(f"HTTP {self.status_code}")

    def json(self) -> Dict[str, Any]:
        return self._payload or {"choices": [{"message": {"content": "# simulated completion"}}]}

    @property
    def ok(self) -> bool:
        return self.status_code < 400


def post(
    url: str,
    headers: Dict[str, str] | None = None,
    json: Dict[str, Any] | None = None,
    **kwargs: Any,
) -> _Response:
    del url, headers, json, kwargs
    return _Response()


def get(
    url: str,
    headers: Dict[str, str] | None = None,
    timeout: float | None = None,
    **kwargs: Any,
) -> _Response:
    del url, headers, timeout, kwargs
    return _Response()
