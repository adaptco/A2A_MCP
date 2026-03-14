"""
Filesystem bridge module.
"""
import re
from pathlib import Path
import logging

logger = logging.getLogger("FileSystemBridge")

class FileSystemBridge:
    """
    Parses code solutions and applies them to the local filesystem.
    Supports markdown code blocks with filename hints.
    """

    @staticmethod
    def extract_files(content: str):
        """
        Extracts files and their content from a string.
        Looks for blocks like:
        
        File: path/to/file.py
        ```python
        code...
        ```
        """
        files = []
        # Pattern to match "File: path" followed by a code block
        # Or just code blocks if they have a language hint that we can map (less reliable)
        pattern = r"File:\s*([^\n]+)\s*```(?:\w+)?\n(.*?)\n```"
        matches = re.finditer(pattern, content, re.DOTALL)

        for match in matches:
            filename = match.group(1).strip()
            code = match.group(2)
            files.append((filename, code))

        return files

    def apply_changes(self, content: str, root_dir: str = "."):
        """Parses content and writes all extracted files to disk."""
        files = self.extract_files(content)
        if not files:
            logger.warning("No files found in content to apply.")
            return False

        root = Path(root_dir)
        for filename, code in files:
            target_path = root / filename
            # Create parent directories if they don't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info("Writing %s bytes to %s", len(code), target_path)
            target_path.write_text(code, encoding="utf-8")

        return True

if __name__ == "__main__":
    # Test snippet
    TEST_CONTENT = """
Here is the solution:

File: hello_world.py
```python
print("Hello from the bridge!")
```

File: data/config.json
```json
{"status": "active"}
```
"""
    bridge = FileSystemBridge()
    bridge.apply_changes(TEST_CONTENT, "tmp_test_bridge")
    print("Test changes applied to tmp_test_bridge/")
