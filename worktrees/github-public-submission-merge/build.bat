@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not exist bin mkdir bin
cl.exe /Iinclude /EHsc /std:c++17 /Fe:bin/ghost-void_engine.exe src/main.cpp src/engine/*.cpp src/agents/*.cpp src/safety/*.cpp src/qube/QubeRuntime.cpp
cl.exe /Iinclude /EHsc /std:c++17 /Fe:bin/jurassic_pixels_test.exe tests/jurassic_pixels_test.cpp src/engine/*.cpp src/agents/*.cpp src/safety/*.cpp src/qube/QubeRuntime.cpp
