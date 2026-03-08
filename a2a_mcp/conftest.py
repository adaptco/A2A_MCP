import sys
import os

repo_root = os.path.abspath(os.path.dirname(__file__))
parent_root = os.path.dirname(repo_root)

# Remove the parent directory if it somehow got onto the path
parent_norm = os.path.normcase(parent_root)
sys.path[:] = [p for p in sys.path if os.path.normcase(os.path.abspath(p)) != parent_norm]

# Ensure the actual repo root is first
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
else:
    sys.path.remove(repo_root)
    sys.path.insert(0, repo_root)

# Fix pywin32 DLL load failure on Windows by adding to PATH
pywin32_path = os.path.join(repo_root, ".venv", "Lib", "site-packages", "pywin32_system32")
if os.path.exists(pywin32_path) and pywin32_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = pywin32_path + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(pywin32_path)
    except AttributeError:
        pass
