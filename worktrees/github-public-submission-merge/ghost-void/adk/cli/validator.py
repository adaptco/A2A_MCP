import os
import json
import yaml
import jsonschema

def load_schema(uri):
    # Mapping fake URIs to local files for RC0
    # In a real environment, this might fetch from a registry
    schema_map = {
        "https://adk.io/schemas/v0/artifact.schema.json": "adk/schemas/artifact.schema.json",
        "https://adk.io/schemas/v0/event.schema.json": "adk/schemas/event.schema.json",
        "https://adk.io/schemas/v0/gate_result.schema.json": "adk/schemas/gate_result.schema.json",
        "https://adk.io/schemas/v0/state.schema.json": "adk/schemas/state.schema.json",
        "https://adk.io/schemas/v0/tool_policy.schema.json": "adk/schemas/tool_policy.schema.json",
        "https://adk.io/schemas/v0/mcp_protocol.schema.json": "adk/schemas/mcp_protocol.schema.json",
    }
    
    local_path = schema_map.get(uri)
    # Adjust path relative to ghost-void root where validation runs
    # If not found in map, try adk/schemas/
    
    if not local_path:
        basename = uri.split("/")[-1]
        potential_path = os.path.join("adk/schemas", basename)
        if os.path.exists(potential_path):
            local_path = potential_path

    if local_path and os.path.exists(local_path):
        with open(local_path, 'r') as f:
            return json.load(f)
    return None

def validate_file(filepath):
    """
    Validates a single file if it declares a known $schema.
    Returns (True, None) on success or skip.
    Returns (False, Error) on failure.
    """
    try:
        with open(filepath, 'r') as f:
            if filepath.endswith('.json'):
                data = json.load(f)
            elif filepath.endswith('.yaml') or filepath.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                return True, None # Skip unknown types
    except Exception as e:
        # Not a valid JSON/YAML file, skip
        return True, None

    if not isinstance(data, dict):
        return True, None

    if "$schema" in data:
        schema_uri = data["$schema"]
        schema = load_schema(schema_uri)
        if schema:
            try:
                jsonschema.validate(instance=data, schema=schema)
                return True, None
            except jsonschema.ValidationError as e:
                return False, f"Validation Error in {filepath}: {e.message}"
            except Exception as e:
                return False, f"Schema Error in {filepath}: {e}"
    
    return True, None


def run_validate(path: str) -> bool:
    """
    Validates artifacts in the given path against ADK schemas.
    """
    print(f"Scanning {path} for artifacts...")
    
    failures = []
    
    for root, _, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            # Skip hidden files and venv/git and node_modules
            if "/." in full_path or "\\." in full_path or "node_modules" in full_path:
                continue
                
            success, error = validate_file(full_path)
            if not success:
                failures.append(error)

    if failures:
        for f in failures:
            print(f)
        return False
        
    print("All artifacts validated successfully.")
    return True
