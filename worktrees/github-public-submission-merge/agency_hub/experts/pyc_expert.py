import marshal
import dis
import sys
import os

def analyze_pyc(pyc_path):
    """
    Analyzes a .pyc file by disassembling its bytecode.
    Returns the disassembled output as a string.
    """
    if not os.path.exists(pyc_path):
        return f"Error: File '{pyc_path}' not found."

    try:
        with open(pyc_path, 'rb') as f:
            # Skip the header (16 bytes for Python 3.7+)
            f.seek(16)
            code_obj = marshal.load(f)
            
            print(f"--- Disassembly for {pyc_path} ---")
            dis.dis(code_obj)
            print("-" * 40)
            
    except Exception as e:
        return f"Error processing {pyc_path}: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pyc_expert.py <path_to_pyc>")
        # Default test if no arg provided
        test_pyc = "avatars/__pycache__/avatar.cpython-311.pyc"
        if os.path.exists(test_pyc):
             analyze_pyc(test_pyc)
    else:
        analyze_pyc(sys.argv[1])
