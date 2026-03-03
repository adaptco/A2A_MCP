import sys
import os
import json

cwd = os.getcwd()
print(f"DEBUG: CWD={cwd}")

ghost_void_path = os.path.abspath(os.path.join(cwd, "ghost-void"))
print(f"DEBUG: ghost_void_path={ghost_void_path}")
sys.path.insert(0, ghost_void_path)

print(f"DEBUG: sys.path={sys.path}")

try:
    import agency_hub
    print(f"DEBUG: agency_hub file={getattr(agency_hub, '__file__', 'NAMESPACE')}")
    from agency_hub import cognitive_tools
    print(f"DEBUG: cognitive_tools file={cognitive_tools.__file__}")
    from agency_hub.cognitive_tools import get_cognitive_manifold_review
    print("DEBUG: Import SUCCESS")
except Exception as e:
    print(f"DEBUG: Import FAILED: {e}")
    import traceback
    traceback.print_exc()

import pipeline
print(f"DEBUG: pipeline file={getattr(pipeline, '__file__', 'NAMESPACE')}")
try:
    from pipeline import manifold
    print(f"DEBUG: manifold file={manifold.__file__}")
except Exception as e:
    print(f"DEBUG: Manifold import FAILED: {e}")
