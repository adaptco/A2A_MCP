CXX := g++
CXXFLAGS := -I./include -std=c++17 -Wall -Wextra
LDFLAGS := 

SRC_DIRS := src src/engine src/agents src/safety src/qube
BUILD_DIR := build
BIN_DIR := bin

SRCS := $(wildcard src/*.cpp) $(wildcard src/engine/*.cpp) $(wildcard src/agents/*.cpp) $(wildcard src/safety/*.cpp) $(filter-out src/qube/QubeMain.cpp, $(wildcard src/qube/*.cpp))
OBJS := $(SRCS:%.cpp=$(BUILD_DIR)/%.o)
DEPS := $(OBJS:.o=.d)

TARGET := $(BIN_DIR)/ghost-void_engine
TARGET_QUBE := $(BIN_DIR)/qube_kernel

.PHONY: all clean test

all: $(TARGET) $(TARGET_QUBE)

$(TARGET): $(OBJS)
	@mkdir -p $(BIN_DIR)
	$(CXX) $(OBJS) -o $@ $(LDFLAGS)

$(TARGET_QUBE): $(BUILD_DIR)/src/qube/QubeMain.o $(BUILD_DIR)/src/qube/QubeRuntime.o
	@mkdir -p $(BIN_DIR)
	$(CXX) $^ -o $@ $(LDFLAGS)

$(BUILD_DIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) -MMD -MP -c $< -o $@

-include $(DEPS)

clean:
	rm -rf $(BUILD_DIR) $(BIN_DIR)

test:
	$(CXX) $(CXXFLAGS) tests/safety_test.cpp src/safety/SafetyLayer.cpp -o $(BIN_DIR)/safety_test
	./$(BIN_DIR)/safety_test

test_engine: $(OBJS)
	# Filter out main.o if it exists in OBJS to avoid multiple main() definitions
	$(CXX) $(CXXFLAGS) tests/engine_test.cpp $(filter-out $(BUILD_DIR)/src/main.o, $(OBJS)) -o $(BIN_DIR)/engine_test
	./$(BIN_DIR)/engine_test

test_jurassic: $(OBJS)
	# Jurassic Pixels verification: Home World + HUB + Synthesis
	$(CXX) $(CXXFLAGS) tests/jurassic_pixels_test.cpp $(filter-out $(BUILD_DIR)/src/main.o, $(OBJS)) -o $(BIN_DIR)/jurassic_pixels_test
	./$(BIN_DIR)/jurassic_pixels_test
