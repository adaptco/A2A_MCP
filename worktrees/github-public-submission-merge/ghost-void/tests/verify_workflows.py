
import os
import sys
from pathlib import Path

def verify_workflows():
    workflows_dir = Path(".agent/workflows")
    if not workflows_dir.exists():
        print(f"Error: {workflows_dir} does not exist.")
        return False

    workflows = list(workflows_dir.glob("*.md"))
    if not workflows:
        print("Warning: No workflows found to verify.")
        return True

    success = True
    for wf in workflows:
        content = wf.read_text()
        if "description:" not in content:
            print(f"Error: Workflow {wf.name} is missing a description in frontmatter.")
            success = False
        
        # Simple check for steps
        if "1." not in content:
            print(f"Error: Workflow {wf.name} seems to be missing numbered steps.")
            success = False
            
    if success:
        print(f"Successfully verified {len(workflows)} workflows.")
    return success

if __name__ == "__main__":
    if not verify_workflows():
        sys.exit(1)
