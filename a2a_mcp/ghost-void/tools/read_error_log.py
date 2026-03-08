import sys
import os

LOG_FILE = "log.txt"

def main():
    if not os.path.exists(LOG_FILE):
        print(f"Error: {LOG_FILE} not found.")
        return

    try:
        with open(LOG_FILE, 'rb') as f:
            content = f.read()
            # Try decoding as UTF-16LE (common for Windows logs) or mbcs
            try:
                text = content.decode('utf-16')
            except UnicodeDecodeError:
                text = content.decode('mbcs', errors='ignore')
            
            lines = text.splitlines()
            for line in lines:
                lower_line = line.lower()
                if "error" in lower_line or "fatal" in lower_line or "unresolved" in lower_line:
                    print(line.strip())

    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    main()
