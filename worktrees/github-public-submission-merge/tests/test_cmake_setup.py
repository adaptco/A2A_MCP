import pytest
import subprocess
import sys
from pathlib import Path
import shutil

# The root of the project
PROJECT_ROOT = Path(__file__).parent.parent
# The directory where the cmake tests will be run
CMAKE_TEST_DIR = PROJECT_ROOT / "tests" / "cmake_test_builds"

@pytest.fixture(autouse=True)
def setup_teardown():
    """Create and clean the test directory for each test."""
    if CMAKE_TEST_DIR.exists():
        shutil.rmtree(CMAKE_TEST_DIR)
    CMAKE_TEST_DIR.mkdir(parents=True)
    yield
    shutil.rmtree(CMAKE_TEST_DIR)

def run_cmake_test(test_name, setup_dirs, setup_files, cmake_root_relative):
    """
    A helper function to run a cmake test.

    :param test_name: The name of the test, used for the test directory.
    :param setup_dirs: A list of directories to create for the test.
    :param setup_files: A list of files to create for the test.
    :param cmake_root_relative: The relative path to the root for cmake.
    """
    test_dir = CMAKE_TEST_DIR / test_name
    test_dir.mkdir()

    for d in setup_dirs:
        (test_dir.parent / d).mkdir(parents=True, exist_ok=True)

    for f in setup_files:
        (test_dir.parent / f).touch(exist_ok=True)

    cmakelists_content = f"""
cmake_minimum_required(VERSION 3.10)
project({test_name})
include({cmake_root_relative}/scripts/setup.cmake)
"""
    (test_dir / "CMakeLists.txt").write_text(cmakelists_content)

    process = subprocess.run(
        ["cmake", "."],
        cwd=test_dir,
        capture_output=True,
        text=True,
    )
    return process.stdout + process.stderr


def test_setup_pass_all_dirs_exist():
    """
    Tests that the setup script passes when all required directories and files exist.
    """
    output = run_cmake_test(
        "pass_all_dirs_exist",
        ["src", "include", "orchestrator", "agents", "schemas", "bin"],
        ["bin/ghost-void_engine.exe"],
        "../../.."
    )
    assert "Verified directory: src" in output
    assert "Verified directory: include" in output
    assert "Verified directory: orchestrator" in output
    assert "Verified directory: agents" in output
    assert "Verified directory: schemas" in output
    assert "Verified engine binary in /bin" in output
    assert "Missing expected directory" not in output
    assert "Ghost-Void Engine binary not found" not in output
    assert "A2A_MCP Setup Validation Complete." in output

def test_setup_fail_missing_dirs():
    """
    Tests that the setup script shows warnings for missing directories.
    """
    output = run_cmake_test(
        "fail_missing_dirs",
        ["src"],
        [],
        "../../.."
    )
    assert "Verified directory: src" in output
    assert "Missing expected directory: include" in output
    assert "Missing expected directory: orchestrator" in output
    assert "Missing expected directory: agents" in output
    assert "Missing expected directory: schemas" in output
    assert "Ghost-Void Engine binary not found" in output
    assert "A2A_MCP Setup Validation Complete." in output


def test_setup_warn_engine_missing():
    """
    Tests that the setup script shows a warning if the engine binary is missing.
    """
    output = run_cmake_test(
        "warn_engine_missing",
        ["src", "include", "orchestrator", "agents", "schemas"],
        [],
        "../../.."
    )
    assert "Verified directory: src" in output
    assert "Verified directory: include" in output
    assert "Verified directory: orchestrator" in output
    assert "Verified directory: agents" in output
    assert "Verified directory: schemas" in output
    assert "Ghost-Void Engine binary not found" in output
    assert "Missing expected directory" not in output
    assert "A2A_MCP Setup Validation Complete." in output

