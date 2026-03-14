cmake_minimum_required(VERSION 3.10)
project(ghostvoid)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Output directory
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)

include_directories(${CMAKE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/src)

# Find all source files in src subdirectories
file(GLOB_RECURSE SOURCES
    "src/engine/*.cpp"
    "src/agents/*.cpp"
    "src/qube/*.cpp"
    "src/bridge/*.cpp"
    "src/safety/*.cpp"
)

# Executable: Main Game Engine
add_executable(ghost-void_engine src/main.cpp ${SOURCES})

# Shared Library
# Exclude main.cpp from the shared library
set(LIB_SOURCES ${SOURCES})
list(FILTER LIB_SOURCES EXCLUDE REGEX "src/main.cpp$")
add_library(ghostvoid SHARED ${LIB_SOURCES})

# Ensure the output name is libghostvoid.so (or .dll on Windows)
set_target_properties(ghostvoid PROPERTIES PREFIX "lib")

if (WIN32)
    # create a proper libghostvoid.dll on windows
    set_target_properties(ghostvoid PROPERTIES SUFFIX ".dll")
endif()

# Executable: Jurassic Pixels Test
add_executable(jurassic_pixels_test src/main.cpp ${SOURCES})

# Minimal Test Target
# add_executable(hello_world src/simple_main.cpp)
