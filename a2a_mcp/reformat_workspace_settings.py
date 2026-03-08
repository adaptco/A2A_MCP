"""
Module to reformat the VS Code workspace settings file.
"""
import json
import os

SETTINGS_PATH = r'c:\Users\eqhsp\.antigravity\A2A_MCP\A2A_MCP\.vscode\settings.json'
try:
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)

    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print("REFORMAT_WORKSPACE_SUCCESS")
except (IOError, json.JSONDecodeError) as e:
    print(f"REFORMAT_WORKSPACE_ERROR: {e}")
