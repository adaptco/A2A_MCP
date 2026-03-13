import hashlib
import json

def normalize_newlines(text: str) -> str:
    """Ensures all newlines are LF (\n)."""
    return text.replace('\r\n', '\n')

def get_artifact_hash(artifact_dict: dict) -> str:
    """
    Computes a deterministic SHA256 hash of a dictionary.
    - Normalizes newlines in string values.
    - Serializes with sort_keys=True and no extra whitespace.
    """
    # Deep copy to avoid mutating original
    normalized = json.loads(json.dumps(artifact_dict))
    
    def recursive_normalize(obj):
        if isinstance(obj, dict):
            return {k: recursive_normalize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [recursive_normalize(v) for v in obj]
        elif isinstance(obj, str):
            return normalize_newlines(obj)
        else:
            return obj

    normalized = recursive_normalize(normalized)
    
    # Force deterministic JSON
    json_bytes = json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=True,
        separators=(',', ':')
    ).encode('utf-8')
    
    return hashlib.sha256(json_bytes).hexdigest()

def get_file_content_hash(content: str) -> str:
    """Hashes file content after normalizing newlines."""
    normalized_content = normalize_newlines(content)
    return hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()
