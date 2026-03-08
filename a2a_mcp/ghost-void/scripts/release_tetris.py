
import os
import zipfile
import shutil
from pathlib import Path

def create_release_bundle():
    """
    Bundles the Tetris observer, related schemas, and tests into a zip for release.
    """
    project_root = Path(__file__).parent.parent
    dist_dir = project_root / "dist"
    dist_dir.mkdir(exist_ok=True)
    
    bundle_name = "tetris_package_v1.zip"
    bundle_path = dist_dir / bundle_name
    
    # Files to include
    files_to_bundle = [
        ("middleware/observers/tetris.py", "middleware/observers/tetris.py"),
        ("middleware/__init__.py", "middleware/__init__.py"),
        ("schemas/model_artifact.py", "schemas/model_artifact.py"),
        ("schemas/agent_artifacts.py", "schemas/agent_artifacts.py"),
        ("tests/test_tetris_aggregation.py", "tests/test_tetris_aggregation.py"),
        ("tests/test_tetris_observer.py", "tests/test_tetris_observer.py"),
    ]
    
    print(f"Creating bundle: {bundle_path}")
    with zipfile.ZipFile(bundle_path, 'w') as zipf:
        for src_rel, arc_rel in files_to_bundle:
            src_path = project_root / src_rel
            if src_path.exists():
                zipf.write(src_path, arc_rel)
                print(f"  Added: {src_rel}")
            else:
                print(f"  Warning: {src_rel} not found!")

    print(f"\nBundle created successfully at: {bundle_path}")

if __name__ == "__main__":
    create_release_bundle()
