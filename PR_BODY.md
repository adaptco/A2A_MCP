## 🧹 Code Health Improvement: Refactor Obstacle Density Dictionary

### 🎯 What
Moved the `mapping` dictionary in `GameEngine._normalize_obstacle_density` to a class attribute `GameEngine.OBSTACLE_DENSITY_MAPPING`.

### 💡 Why
This prevents the dictionary from being recreated every time `_normalize_obstacle_density` is called, which is a minor performance optimization and improves code readability by separating data from logic.

### ✅ Verification
- Ran `tests/test_webgl_integration.py` which covers `GameEngine` functionality.
- Ran the full test suite to ensure no regressions.
- Verified that `_normalize_obstacle_density` correctly accesses the class attribute.

### ✨ Result
Cleaner code and slightly better performance for obstacle density normalization.
