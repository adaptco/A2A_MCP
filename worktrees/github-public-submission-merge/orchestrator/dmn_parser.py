import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class ValidationReport:
    valid: bool
    reasons: List[str]

@dataclass
class Receipt:
    hash: str
    timestamp: str
    parser_version: str
    verdict: str

class DMNParser:
    VERSION = "1.0.0"

    def parse(self, input_data: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], ValidationReport, Receipt]:
        """
        Parses DMN input, validates geometry and constitution, and returns canonical AST.
        """
        # 1. Canonicalize Input (Sort keys for determinism)
        canonical_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        # 2. Validate Geometry
        geo_report = self._validate_geometry(input_data)
        if not geo_report.valid:
            return None, geo_report, self._mint_receipt(input_hash, "REJECTED_GEOMETRY")

        # 3. Enforce Constitution
        const_report = self._enforce_constitution(input_data)
        if not const_report.valid:
            return None, const_report, self._mint_receipt(input_hash, "REJECTED_CONSTITUTION")

        # 4. Construct Canonical AST
        ast = self._build_ast(input_data)

        return ast, ValidationReport(True, []), self._mint_receipt(input_hash, "ACCEPTED")

    def _validate_geometry(self, data: Dict[str, Any]) -> ValidationReport:
        reasons = []
        if "nodes" not in data or not isinstance(data["nodes"], list):
            reasons.append("Missing or invalid 'nodes' list.")

        if "edges" not in data or not isinstance(data["edges"], list):
            reasons.append("Missing or invalid 'edges' list.")

        # Check node types
        valid_types = {"Structural", "Behavioral", "Visual"}
        if "nodes" in data:
            for node in data["nodes"]:
                if node.get("type") not in valid_types:
                    reasons.append(f"Invalid node type: {node.get('type')}")
                if "id" not in node:
                    reasons.append("Node missing 'id'")

        return ValidationReport(len(reasons) == 0, reasons)

    def _enforce_constitution(self, data: Dict[str, Any]) -> ValidationReport:
        reasons = []
        # Example Constitutional Rule: No self-referential edges
        if "edges" in data:
            for edge in data["edges"]:
                if edge.get("source") == edge.get("target"):
                    reasons.append(f"Self-referential edge detected: {edge.get('source')}")

        return ValidationReport(len(reasons) == 0, reasons)

    def _build_ast(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Return a normalized dictionary structure
        return {
            "version": self.VERSION,
            "graph": {
                "nodes": sorted(data["nodes"], key=lambda x: x["id"]),
                "edges": sorted(data["edges"], key=lambda x: (x["source"], x["target"]))
            }
        }

    def _mint_receipt(self, data_hash: str, verdict: str) -> Receipt:
        from datetime import datetime, timezone
        return Receipt(
            hash=data_hash,
            timestamp=datetime.now(timezone.utc).isoformat(),
            parser_version=self.VERSION,
            verdict=verdict
        )
