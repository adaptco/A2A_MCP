import json
import os
from typing import List, Dict, Any, Callable

class DockerMCPCatalog:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found at {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)

    def _is_path_allowed(self, path: str, operation: str) -> bool:
        """Checks if a given path is allowed for a given operation."""
        abs_path = os.path.abspath(path)
        for allowed_path_info in self.config:
            allowed_path = os.path.abspath(allowed_path_info["path"])
            if abs_path.startswith(allowed_path):
                if operation == 'write' and allowed_path_info.get('readOnly', False):
                    return False  # Write operation not allowed on read-only paths
                return True  # Path is within an allowed directory
        return False

    def read_file(self, path: str) -> str:
        """Reads the content of a file."""
        if not self._is_path_allowed(path, 'read'):
            raise PermissionError(f"Read access denied for path: {path}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")
        with open(path, 'r') as f:
            return f.read()

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a file."""
        if not self._is_path_allowed(path, 'write'):
            raise PermissionError(f"Write access denied for path: {path}")
        
        # Ensure the directory exists
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        with open(path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {path}"

    def list_directory(self, path: str) -> List[str]:
        """Lists the content of a directory."""
        if not self._is_path_allowed(path, 'read'):
            raise PermissionError(f"Read access denied for path: {path}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        return os.listdir(path)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Returns the list of tools provided by this server."""
        return [
            {
                "name": "docker_mcp_catalog_read_file",
                "description": "Reads the content of a file from the allowed paths.",
                "function": self.read_file,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path to the file to read."}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "docker_mcp_catalog_write_file",
                "description": "Writes content to a file in the allowed paths.",
                "function": self.write_file,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path of the file to write to."},
                        "content": {"type": "string", "description": "The content to write."}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "docker_mcp_catalog_list_directory",
                "description": "Lists the content of a directory from the allowed paths.",
                "function": self.list_directory,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "The path to the directory to list."}
                    },
                    "required": ["path"]
                }
            }
        ]

# Example of how it might be used
if __name__ == '__main__':
    # This part is for demonstration and testing
    # In a real scenario, this server would be loaded by the MCP framework
    config_file = os.path.join(os.path.dirname(__file__), 'docker-mcp-catalog.json')
    catalog_server = DockerMCPCatalog(config_file)
    print("Docker MCP Catalog server loaded.")
    
    tools = catalog_server.get_tools()
    print(f"Provided tools: {[tool['name'] for tool in tools]}")
    
    # Example usage of the tools (for testing)
    try:
        print("\n--- Testing list_directory ---")
        # Trying to list a directory that is not allowed. This should fail.
        try:
            catalog_server.list_directory("/tmp")
        except PermissionError as e:
            print(f"Correctly caught expected error: {e}")

        # Assuming /safe_path/for/io is a directory you can create for testing
        safe_dir = "/safe_path/for/io"
        if not os.path.exists(safe_dir):
            os.makedirs(safe_dir)
        print(f"Listing allowed directory '{safe_dir}': {catalog_server.list_directory(safe_dir)}")


        print("\n--- Testing write_file and read_file ---")
        test_file_path = os.path.join(safe_dir, "test_file.txt")
        
        # Writing to an allowed path
        print(catalog_server.write_file(test_file_path, "Hello from Docker MCP Catalog!"))
        
        # Reading from an allowed path
        print(f"Reading file '{test_file_path}': {catalog_server.read_file(test_file_path)}")

        # Trying to write to a read-only path. This should fail.
        readonly_file_path = "/readonly_path/test.txt"
        try:
            catalog_server.write_file(readonly_file_path, "should fail")
        except PermissionError as e:
            print(f"Correctly caught expected error: {e}")

    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")

