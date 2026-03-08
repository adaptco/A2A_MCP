import os
import re
from typing import Optional

_PLAN_ID_RE = re.compile(r"[A-Za-z0-9_\-\.]+")


def extract_plan_id_from_path(path: str) -> Optional[str]:
    """
    Given a filesystem-like path (e.g. 'orchestrator/plans/ingress.py',
    '.github/workflows/plans/ingress/<plan-id>.yml', or '.github/workflows/plans/ingress/<plan-id>'),
    return a sanitized plan_id from the basename.

    Returns None if no sane plan id could be found.
    """
    if not path:
        return None

    normalized = path.replace("\\", "/")
    base = os.path.basename(normalized)
    name, _ext = os.path.splitext(base)
    if not name:
        return None

    m = _PLAN_ID_RE.match(name)
    if m:
        return m.group(0)

    safe = re.sub(r"[^A-Za-z0-9_\-\.]", "-", name)
    return safe
