from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


_IMPL = Path(__file__).with_name("bytesampler-adapter.py")
_SPEC = importlib.util.spec_from_file_location("bytesampler_adapter_impl", _IMPL)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load adapter implementation from {_IMPL}")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MOD
_SPEC.loader.exec_module(_MOD)

sha256_hex = _MOD.sha256_hex
jcs_dumps = _MOD.jcs_dumps
digest_jcs = _MOD.digest_jcs
SampleResult = _MOD.SampleResult
Mulberry32 = _MOD.Mulberry32
seed_u32_from_sha256_hex = _MOD.seed_u32_from_sha256_hex
weighted_choice = _MOD.weighted_choice
sample_covering_tree = _MOD.sample_covering_tree
