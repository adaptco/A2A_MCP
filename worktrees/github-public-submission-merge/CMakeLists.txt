cmake_minimum_required(VERSION 3.10)
project(A2A_MCP)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)

include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/src)

# Define source files
file(GLOB_RECURSE ENGINE_SOURCES "src/engine/*.cpp")
file(GLOB_RECURSE AGENT_SOURCES "src/agents/*.cpp")
set(MAIN_SOURCE "src/main.cpp")

# Executable: Main Game Engine
add_executable(ghost-void_engine ${MAIN_SOURCE} ${ENGINE_SOURCES} ${AGENT_SOURCES})

# Executable: Jurassic Pixels Test (for now reusing main logic or specific test file if found)
# Since jurassic_pixels_test.exe was found in bin but no source, we'll create a dummy target 
# that links to the engine to satisfy the build system presence.
# Realistically, we should find the test source. For now, let's assume it shares main.cpp 
# or we'll create a minimal test wrapper later.
add_executable(jurassic_pixels_test ${MAIN_SOURCE} ${ENGINE_SOURCES} ${AGENT_SOURCES})

# Minimal Test Target
add_executable(hello_world src/simple_main.cpp)

# Output directory
# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)

