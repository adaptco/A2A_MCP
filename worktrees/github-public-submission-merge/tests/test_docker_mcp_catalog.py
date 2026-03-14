import pytest
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

# Make sure the server module is in the python path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mcp_servers.docker_mcp_catalog.server import DockerMCPCatalog

@pytest.fixture
def temp_config_file():
    """Creates a temporary config file for testing."""
    config_data = [
        {"path": "/tmp/safe_area", "readOnly": False},
        {"path": "/tmp/read_only_area", "readOnly": True},
    ]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as f:
        json.dump(config_data, f)
        config_path = f.name
    
    # Create the directories for testing
    os.makedirs("/tmp/safe_area", exist_ok=True)
    os.makedirs("/tmp/read_only_area", exist_ok=True)

    yield config_path
    
    os.remove(config_path)
    # Clean up created directories and files
    import shutil
    if os.path.exists("/tmp/safe_area"):
        shutil.rmtree("/tmp/safe_area")
    if os.path.exists("/tmp/read_only_area"):
        shutil.rmtree("/tmp/read_only_area")


@pytest.fixture
def catalog_server(temp_config_file):
    """Initializes the DockerMCPCatalog server with the temp config."""
    # Temporarily adjust config to use the temp paths
    with open(temp_config_file, 'r') as f:
        config = json.load(f)
    
    safe_area = os.path.join(tempfile.gettempdir(), "safe_area")
    read_only_area = os.path.join(tempfile.gettempdir(), "read_only_area")
    
    os.makedirs(safe_area, exist_ok=True)
    os.makedirs(read_only_area, exist_ok=True)
    
    config[0]["path"] = safe_area
    config[1]["path"] = read_only_area
    
    with open(temp_config_file, 'w') as f:
        json.dump(config, f)

    return DockerMCPCatalog(temp_config_file)


def test_load_config(catalog_server):
    """Tests that the configuration is loaded correctly."""
    assert len(catalog_server.config) == 2
    assert "safe_area" in catalog_server.config[0]["path"]
    assert not catalog_server.config[0]["readOnly"]
    assert "read_only_area" in catalog_server.config[1]["path"]
    assert catalog_server.config[1]["readOnly"]

def test_load_config_file_not_found():
    """Tests that a FileNotFoundError is raised for a non-existent config."""
    with pytest.raises(FileNotFoundError):
        DockerMCPCatalog("/non/existent/path.json")

def test_is_path_allowed(catalog_server):
    """Tests the _is_path_allowed method."""
    safe_path = os.path.join(tempfile.gettempdir(), "safe_area", "file.txt")
    readonly_path = os.path.join(tempfile.gettempdir(), "read_only_area", "file.txt")
    unsafe_path = "/somewhere/else/file.txt"

    # Test read operations
    assert catalog_server._is_path_allowed(safe_path, 'read')
    assert catalog_server._is_path_allowed(readonly_path, 'read')
    assert not catalog_server._is_path_allowed(unsafe_path, 'read')

    # Test write operations
    assert catalog_server._is_path_allowed(safe_path, 'write')
    assert not catalog_server._is_path_allowed(readonly_path, 'write')
    assert not catalog_server._is_path_allowed(unsafe_path, 'write')

def test_read_file(catalog_server):
    """Tests the read_file tool."""
    safe_path = os.path.join(tempfile.gettempdir(), "safe_area", "test.txt")
    with open(safe_path, 'w') as f:
        f.write("hello")
    
    assert catalog_server.read_file(safe_path) == "hello"

    with pytest.raises(PermissionError):
        catalog_server.read_file("/unsafe/path.txt")
    
    with pytest.raises(FileNotFoundError):
        catalog_server.read_file(os.path.join(tempfile.gettempdir(), "safe_area", "non_existent.txt"))

def test_write_file(catalog_server):
    """Tests the write_file tool."""
    safe_path = os.path.join(tempfile.gettempdir(), "safe_area", "test_write.txt")
    
    result = catalog_server.write_file(safe_path, "new content")
    assert result == f"Successfully wrote to {safe_path}"
    with open(safe_path, 'r') as f:
        assert f.read() == "new content"

    readonly_path = os.path.join(tempfile.gettempdir(), "read_only_area", "test.txt")
    with pytest.raises(PermissionError):
        catalog_server.write_file(readonly_path, "should not work")

    with pytest.raises(PermissionError):
        catalog_server.write_file("/unsafe/path.txt", "should not work")

def test_list_directory(catalog_server):
    """Tests the list_directory tool."""
    safe_dir = os.path.join(tempfile.gettempdir(), "safe_area")
    open(os.path.join(safe_dir, "f1.txt"), 'w').close()
    open(os.path.join(safe_dir, "f2.txt"), 'w').close()

    content = catalog_server.list_directory(safe_dir)
    assert "f1.txt" in content
    assert "f2.txt" in content

    with pytest.raises(PermissionError):
        catalog_server.list_directory("/unsafe_dir")

    with pytest.raises(FileNotFoundError):
        catalog_server.list_directory(os.path.join(safe_dir, "non_existent_dir"))

def test_get_tools(catalog_server):
    """Tests that get_tools returns the correct tool definitions."""
    tools = catalog_server.get_tools()
    assert len(tools) == 3
    
    tool_names = [t['name'] for t in tools]
    assert "docker_mcp_catalog_read_file" in tool_names
    assert "docker_mcp_catalog_write_file" in tool_names
    assert "docker_mcp_catalog_list_directory" in tool_names
