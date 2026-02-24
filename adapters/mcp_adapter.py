import json
import hashlib
import copy
import logging
import os
import requests
from requests.exceptions import RequestException, Timeout
from typing import Dict, Any
from schemas.events import RuntimeEvent, EventPayload

# Physical Constants Configuration
SYMMETRY_MODE = "C5_SYMMETRY"
WHEEL_SPEC = {
    "model": "Advan GT Beyond",
    "geometry": "5-spoke",
    "finish": "Racing Sand Metallic (RSM)",
    "allowed_variations": []  # Strictly blocks 6, 7, or 10-spoke configurations
}
TARGET_VEHICLE_MODELS = ["Vantage", "VH100", "Supra", "A90"]
TARGET_PAINT_FINISH = "Obsidian/Nocturnal Black"

logger = logging.getLogger(__name__)

class MCPToolAdapter:
    """
    Anti-corruption layer for external tool execution via MCP.
    Intercepts tool calls to enforce strict system parameters before execution.
    """
    def __init__(self, mcp_client=None):
        # Retrieve the MCP server URL from environment variables
        self.server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
        self.client = mcp_client

    MAX_RESPONSE_BYTES = 2_000_000  # 2MB ceiling

    def _canonical_json(self, obj: Dict[str, Any]) -> str:
        """Deterministic JSON serialization for hashing/replay"""
        return json.dumps(
            obj, 
            sort_keys=True, 
            separators=(",", ":"), 
            ensure_ascii=False
        )

    def _sha256_hex(self, data: str) -> str:
        """Stable hash for receipts/VVL"""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def execute(self, event: RuntimeEvent) -> EventPayload:
        tool_name = event.payload.data.get("tool_name")
        arguments = copy.deepcopy(event.payload.data.get("arguments", {}))
        
        logger.info(f"Executing tool: {tool_name} for trace: {event.metadata.trace_id}")
        
        # Intercept and mutate arguments for rendering operations (VH2 constitutional enforcement)
        if tool_name == "render_vehicle_asset":
            arguments = self._enforce_physical_constants(arguments)
        
        # Prepare MCP payload
        mcp_payload = {
            "tool_name": tool_name,
            "arguments": arguments,
            "trace_id": str(event.metadata.trace_id)
        }
        
        # 1️⃣ CANONICAL SERIALIZATION + HASH (MANDATORY)
        canonical_body = self._canonical_json(mcp_payload)
        request_hash = self._sha256_hex(canonical_body)
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VH2-ControlBus/1.0"
        }
        if token := os.getenv("MCP_AUTH_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
        
        try:
            # 2️⃣ HTTP CALL WITH CANONICAL BODY
            response = requests.post(
                f"{self.server_url}/execute",
                data=canonical_body,  # Use canonical bytes, not json= (non-deterministic)
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            # 3️⃣ BOUNDED RESPONSE + SCHEMA (MANDATORY)
            raw = response.content
            if len(raw) > self.MAX_RESPONSE_BYTES:
                raise ValueError(f"ERR.RESPONSE_TOO_LARGE: {len(raw)} bytes")
            
            result = json.loads(raw.decode("utf-8"))
            if not isinstance(result, dict) or "status" not in result:
                raise ValueError("ERR.INVALID_RESPONSE_SHAPE")
            
            # 4️⃣ CANONICAL RESPONSE HASH (REPLAY-GRADE)
            canonical_result = self._canonical_json(result)
            response_hash = self._sha256_hex(canonical_result)
            
            status = "SUCCESS"
            
        except Timeout as e:
            logger.error(f"MCP timeout for {tool_name}: {e}")
            result = {"error": f"MCP Timeout: {e}"}
            status = "ERROR"
            response_hash = None

        except (RequestException, ValueError) as e:
            logger.error(f"MCP failed for {tool_name}: {e}")
            result = {"error": str(e)}
            status = "ERROR"
            response_hash = None
            
        # 5️⃣ DETERMINISTIC RECEIPT (VVL-ready)
        receipt = {
            "receipt_version": "mcp_adapter.v1",
            "trace_id": str(event.metadata.trace_id),
            "tool_name": tool_name,
            "request_hash": request_hash,
            "response_hash": response_hash,
            "status": status,
            "canonical_request_len": len(canonical_body)
        }
        
        return EventPayload(
            type="TOOL_RESULT",
            data={
                "status": status,
                "result": result,
                "tool_name": tool_name,
                "receipt": receipt  # Ledger-ready
            }
        )

    def _enforce_physical_constants(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mutates tool arguments to guarantee strict adherence to canonical geometry,
        symmetry, and material finishes, overriding any agentic drift.
        """
        logging.info("Enforcing physical constants: Overriding symmetry and materials to prevent drift.")
        
        # Lock geometry and structural symmetry
        args["symmetry_mode"] = SYMMETRY_MODE
        args["wheels"] = WHEEL_SPEC.copy()
        
        # Enforce canonical body finishes based on the target asset
        vehicle_model = args.get("vehicle_model", "")
        if any(target in vehicle_model for target in TARGET_VEHICLE_MODELS):
            args["paint_finish"] = TARGET_PAINT_FINISH
            
        return args
