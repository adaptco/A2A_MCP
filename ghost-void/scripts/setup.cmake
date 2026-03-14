# CMake Setup Script for A2A_MCP Project
# This script validates the presence of core directories and compiles basic checks.

message(STATUS "Initializing A2A_MCP Environment Setup...")

set(REQUIRED_DIRS 
    "src"
    "include"
    "orchestrator"
    "agents"
    "schemas"
)

foreach(DIR IN LISTS REQUIRED_DIRS)
    if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../${DIR}")
        message(WARNING "Missing expected directory: ${DIR}")
    else()
        message(STATUS "Verified directory: ${DIR}")
    endif()
endforeach()

# Check for Engine Binary
<<<<<<< HEAD
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../bin/ghost-void_engine.exe" OR EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../bin/ghost-void_engine")
    message(STATUS "Verified engine binary exists.")
else()
    message(WARNING "Ghost-Void Engine binary not found. You can build the project by executing:")
    message(STATUS "  cmake -S . -B build")
    message(STATUS "  cmake --build build --config Release")
=======
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../bin/ghost-void_engine.exe")
    message(STATUS "Verified engine binary in /bin")
else()
    message(WARNING "Ghost-Void Engine binary not found. Please build the project.")
>>>>>>> origin/main
endif()

message(STATUS "A2A_MCP Setup Validation Complete.")
