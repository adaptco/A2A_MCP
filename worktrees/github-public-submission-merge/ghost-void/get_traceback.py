import sys
import os
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

try:
    from rbac.rbac_service import app
    print("Import successful")
except Exception:
    traceback.print_exc()
