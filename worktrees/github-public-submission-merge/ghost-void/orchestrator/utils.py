# A2A_MCP/orchestrator/utils.py
import os
import re
from typing import Optional

_PLAN_ID_RE = re.compile(r"[A-Za-z0-9_\-\.]+")

def extract_plan_id_from_path(path: str) -> Optional[str]:
    """
    Given a filesystem-like path (e.g. '.github/workflows/plans/ingress/<plan-id>.yml'
    or '.github/workflows/plans/ingress/<plan-id>'), return a sanitized plan_id.

    Returns None if no sane plan id could be found.
    """
    if not path:
        return None
    # Normalize separators
    normalized = path.replace("\\", "/")
    # Take basename
    base = os.path.basename(normalized)
    # Remove extension
    name, _ext = os.path.splitext(base)
    if not name:
        return None
    # Keep only safe characters (alnum, -, _, .)
    m = _PLAN_ID_RE.match(name)
    if m:
        return m.group(0)
    # Fallback: keep name but replace problematic chars
    safe = re.sub(r"[^A-Za-z0-9_\-\.]", "-", name)
    return safe
