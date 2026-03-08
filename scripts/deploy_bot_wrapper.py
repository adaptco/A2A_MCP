#!/usr/bin/env python3
"""
scripts/deploy_bot_wrapper.py - Python wrapper for deployment bot
Usage: python scripts/deploy_bot_wrapper.py (from project root)
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Path to deployment bot
    bot_script = project_root / "deployment_bot.py"
    
    if not bot_script.exists():
        print(f"Error: {bot_script} not found")
        sys.exit(1)
    
    # Change to project root
    os.chdir(project_root)
    
    # Run deployment_bot.py with full-deploy action
    cmd = [sys.executable, str(bot_script), "full-deploy"]
    
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\nDeployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error running deployment bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
