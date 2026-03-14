import json
import pytest
from pathlib import Path
from main import AvatarRegistry

@pytest.fixture
def registry_data():
    return {
        "mesh": {
            "version": "1.0",
            "environment": "test"
        },
        "avatars": [
            {
                "name": "TestAvatar",
                "elemental_alignment": "Void",
                "capsule_domain": "void.domain"
            },
            {
                "name": "FireAvatar",
                "elemental_alignment": "Fire",
                "capsule_domain": "fire.domain"
            }
        ]
    }

@pytest.fixture
def registry_file(tmp_path, registry_data):
    p = tmp_path / "avatar_registry.json"
    with open(p, "w") as f:
        json.dump(registry_data, f)
    return p

def test_load_registry(registry_file, registry_data):
    registry = AvatarRegistry(registry_file)
    assert registry.mesh() == registry_data["mesh"]
    assert len(registry.list()) == 2
    assert "TestAvatar" in registry.available_names()
    assert "FireAvatar" in registry.available_names()

def test_get_existing_avatar(registry_file, registry_data):
    registry = AvatarRegistry(registry_file)
    avatar = registry.get("TestAvatar")
    assert avatar is not None
    assert avatar["name"] == "TestAvatar"
    assert avatar["elemental_alignment"] == "Void"

def test_get_avatar_case_insensitive(registry_file, registry_data):
    registry = AvatarRegistry(registry_file)
    avatar_lower = registry.get("testavatar")
    avatar_upper = registry.get("TESTAVATAR")

    assert avatar_lower is not None
    assert avatar_upper is not None
    assert avatar_lower["name"] == "TestAvatar"
    assert avatar_upper["name"] == "TestAvatar"

def test_get_non_existent_avatar(registry_file):
    registry = AvatarRegistry(registry_file)
    avatar = registry.get("NonExistentAvatar")
    assert avatar is None

def test_get_edge_cases(registry_file):
    registry = AvatarRegistry(registry_file)
    assert registry.get("") is None
    assert registry.get(None) is None
    assert registry.get("   ") is None
