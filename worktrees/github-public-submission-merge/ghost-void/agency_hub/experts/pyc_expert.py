import marshal
import dis
import sys
import types
from pathlib import Path
from typing import Dict, List, Any, Optional

class PycExpert:
    """
    Expert agent specializing in disassembling and modeling Python compiled bytecode (.pyc).
    Provides deep structural insights for the Orchestration Model.
    """

    def __init__(self):
        self.disassembly_registry = {}

    def analyze_pyc(self, file_path: str) -> Dict[str, Any]:
        """
        Reads a .pyc file and returns its disassembled structure and modeling metadata.
        """
        path = Path(file_path)
        if not path.exists():
            return {"status": "ERROR", "message": f"File {file_path} not found."}

        try:
            with open(path, 'rb') as f:
                # Python 3.7+ magic number + 4-byte bit field + 4 or 8 byte timestamp + size
                # Usually skip 16 bytes for Python 3.7+ (magic, bitfield, timestamp, size)
                f.read(16)
                code_obj = marshal.load(f)

            if not isinstance(code_obj, types.CodeType):
                return {"status": "ERROR", "message": "Loaded object is not a valid code object."}

            return {
                "status": "SUCCESS",
                "filename": code_obj.co_filename,
                "name": code_obj.co_name,
                "constants": [str(c) for c in code_obj.co_consts],
                "names": list(code_obj.co_names),
                "varnames": list(code_obj.co_varnames),
                "bytecode_disassembly": self._get_disassembly(code_obj),
                "modeling_insights": self._generate_modeling_insights(code_obj)
            }

        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def _get_disassembly(self, code_obj: types.CodeType) -> str:
        """
        Encapsulates the bytecode disassembly logic.
        """
        import io
        stdout = io.StringIO()
        dis.dis(code_obj, file=stdout)
        return stdout.getvalue()

    def _generate_modeling_insights(self, code_obj: types.CodeType) -> Dict[str, Any]:
        """
        Models the language structure based on bytecode patterns.
        """
        # Extract complexity metrics or pattern signatures
        return {
            "instruction_count": len(code_obj.co_code),
            "stack_size": code_obj.co_stacksize,
            "arg_count": code_obj.co_argcount,
            "has_free_vars": len(code_obj.co_freevars) > 0,
            "modeling_type": "COMPILED_PYTHON_BYTECODE_V1"
        }

if __name__ == "__main__":
    if len(sys.argv) > 1:
        expert = PycExpert()
        result = expert.analyze_pyc(sys.argv[1])
        import json
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python pyc_expert.py <path_to_pyc>")
