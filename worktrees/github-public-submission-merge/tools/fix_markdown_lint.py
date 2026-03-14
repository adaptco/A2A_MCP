
import os

file_path = r"c:\Users\eqhsp\.gemini\antigravity\brain\a0e8471e-baa7-478f-a5ed-fa5ad4c18ebe\implementation_plan.md"

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Fix table separator line 8
    # "8: |-----------|------|------|"
    if stripped.startswith("|") and stripped.endswith("|") and "-" in stripped:
        if stripped.replace("-", "").replace("|", "") == "": # Only separators
             line = "| :--- | :--- | :--- |\n"

    # Fix code block line 18
    # "18: ```"
    # "19: CI/CD Pipeline Runner"
    if stripped == "```" and i + 1 < len(lines):
        next_line = lines[i+1].strip()
        if "CI/CD Pipeline Runner" in next_line:
            line = "```text\n"

    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully applied markdown fixes.")
