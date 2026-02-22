import ast
import os

for root, dirs, files in os.walk("tests"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r") as f:
                    ast.parse(f.read())
                print(f"OK: {path}")
            except SyntaxError as e:
                print(f"ERROR: {path}: {e}")
            except Exception as e:
                print(f"FAIL: {path}: {e}")
