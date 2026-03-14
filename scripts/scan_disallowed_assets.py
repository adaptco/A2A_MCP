#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Configuration for disallowed patterns
DISALLOWED_EXTENSIONS = {
    ".safetensors",
    ".pt",
    ".bin",
    ".ckpt",
}

MAX_ONNX_SIZE_MB = 100
MAX_FILE_SIZE_MB = 50

DISALLOWED_DIRS = {
    "datasets",
    "corpus",
    "prompts_dump",
    "embeddings_dump",
}

# Vector index signatures
VECTOR_INDEX_SIGNATURES = {
    "qdrant",
    "faiss",
    "milvus",
}

ALLOWLISTED_PATHS = {
    ".git",
    ".venv",
    "node_modules",
    "build",
    "CMakeFiles",
    "worktrees",
    ".pytest_cache",
}

def scan_repo(root_path: Path):
    violations = []

    for root, dirs, files in os.walk(root_path):
        rel_root = Path(root).relative_to(root_path)
        
        # Skip allowlisted paths
        if any(part in ALLOWLISTED_PATHS for part in rel_root.parts):
            continue

        # Check for disallowed directories
        for d in dirs:
            if d in DISALLOWED_DIRS:
                violations.append(f"Disallowed directory found: {rel_root / d}")
            
            # Check for vector index signatures in dir names
            if any(sig in d.lower() for sig in VECTOR_INDEX_SIGNATURES):
                violations.append(f"Potential vector index directory found: {rel_root / d}")

        # Check for disallowed files
        for f in files:
            file_path = Path(root) / f
            rel_path = rel_root / f
            
            # Check extensions
            ext = file_path.suffix.lower()
            if ext in DISALLOWED_EXTENSIONS:
                # Heuristic: skip if it's in a build-like directory or looks like a compiler test
                if "build" in str(rel_path).lower() or "cmake" in str(rel_path).lower():
                    continue
                violations.append(f"Disallowed model file extension '{ext}': {rel_path}")

            # Check ONNX size
            if ext == ".onnx":
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > MAX_ONNX_SIZE_MB:
                    violations.append(f"Oversized ONNX file ({size_mb:.2f}MB > {MAX_ONNX_SIZE_MB}MB): {rel_path}")

            # Check general large files
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                violations.append(f"Oversized file ({size_mb:.2f}MB > {MAX_FILE_SIZE_MB}MB): {rel_path}")

    return violations

if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    print(f"Scanning repository at {repo_root} for disallowed assets...")
    
    violations = scan_repo(repo_root)
    
    if violations:
        print("\n[!] CI GATE FAILED: Disallowed assets or large files detected:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("\n[+] CI GATE PASSED: No disallowed assets detected.")
        sys.exit(0)
