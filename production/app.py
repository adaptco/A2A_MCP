from flask import Flask, request, jsonify, make_response
import time
import json
import logging
import hashlib
import uuid
import datetime
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from prometheus_metrics import REQUEST_COUNT, REQUEST_LATENCY, CIRCUIT_BREAKER_STATE, VALIDATION_ERRORS

app = Flask(__name__)

# Config
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30
VERSION = "3.0.0-RELEASE"

# State
circuit_failures = 0
circuit_open_time = 0
circuit_open = False

# Logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("audit")

def check_circuit_breaker():
    global circuit_failures, circuit_open_time, circuit_open
    if circuit_open:
        if time.time() - circuit_open_time > CIRCUIT_BREAKER_TIMEOUT:
            # Half-open / Reset
            circuit_open = False
            circuit_failures = 0
            CIRCUIT_BREAKER_STATE.set(0)
            return True
        return False
    return True

def trip_circuit_breaker():
    global circuit_failures, circuit_open_time, circuit_open
    circuit_failures += 1
    if circuit_failures >= CIRCUIT_BREAKER_THRESHOLD:
        circuit_open = True
        circuit_open_time = time.time()
        CIRCUIT_BREAKER_STATE.set(1)

def audit_log(event_type, status, details=None):
    log_entry = {
        "event_type": event_type,
        "receipt_id": f"RCP-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
        "environment": "PRODUCTION",
        "service_version": VERSION,
        "tool": details.get("tool") if details else None,
        "input_hash": details.get("input_hash") if details else None,
        "output_hash": details.get("output_hash") if details else None,
        "status": status,
        "duration_ms": details.get("duration_ms") if details else None,
        "severity": details.get("severity"),
        "error_code": details.get("error_code")
    }
    logger.info(json.dumps(log_entry))
    return log_entry

@app.route('/health_check', methods=['GET'])
def health_check():
    return jsonify({"status": "UP", "version": VERSION}), 200

@app.route('/metrics', methods=['GET'])
def metrics():
    return make_response(generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST})

@app.route('/vehicle_validate_c5', methods=['POST'])
def vehicle_validate_c5():
    if not check_circuit_breaker():
        return jsonify({"error": "Service Unavailable (Circuit Breaker)"}), 503

    start_time = time.time()
    try:
        data = request.get_json()
        if not data or 'vin' not in data:
            VALIDATION_ERRORS.inc()
            # Do not trip circuit breaker on client errors (DoS vector)
            duration = (time.time() - start_time) * 1000
            audit_log("VEHICLE_MCP_VALIDATION", "FAIL", {"tool": "vehicle_validate_c5", "duration_ms": duration, "error_code": "INVALID_INPUT"})
            return jsonify({"error": "Invalid input: missing 'vin'"}), 400

        # Simulate C5 symmetry check
        input_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
        output_hash = hashlib.sha256(f"validated-{input_hash}".encode()).hexdigest()[:16]

        duration = (time.time() - start_time) * 1000
        receipt = audit_log("VEHICLE_MCP_VALIDATION", "PASS", {
            "tool": "vehicle_validate_c5",
            "input_hash": input_hash,
            "output_hash": output_hash,
            "duration_ms": duration
        })

        REQUEST_COUNT.labels('POST', '/vehicle_validate_c5', '200').inc()
        REQUEST_LATENCY.labels('/vehicle_validate_c5').observe(time.time() - start_time)
        return jsonify(receipt), 200

    except Exception as e:
        trip_circuit_breaker()
        REQUEST_COUNT.labels('POST', '/vehicle_validate_c5', '500').inc()
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/vehicle_compute_witness', methods=['POST'])
def vehicle_compute_witness():
    if not check_circuit_breaker():
        return jsonify({"error": "Service Unavailable (Circuit Breaker)"}), 503

    start_time = time.time()
    try:
        data = request.get_json()
        if not data:
             return jsonify({"error": "No data provided"}), 400

        # Compute SHA-256
        content = json.dumps(data, sort_keys=True).encode()
        witness_hash = hashlib.sha256(content).hexdigest()

        duration = (time.time() - start_time) * 1000
        audit_log("VEHICLE_MCP_WITNESS", "PASS", {
            "tool": "vehicle_compute_witness",
            "output_hash": witness_hash,
            "duration_ms": duration
        })

        REQUEST_COUNT.labels('POST', '/vehicle_compute_witness', '200').inc()
        REQUEST_LATENCY.labels('/vehicle_compute_witness').observe(time.time() - start_time)
        return jsonify({"witness_hash": witness_hash}), 200
    except Exception as e:
        trip_circuit_breaker()
        REQUEST_COUNT.labels('POST', '/vehicle_compute_witness', '500').inc()
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/vehicle_normalize_data', methods=['POST'])
def vehicle_normalize_data():
    """
    Applies MCP Dot Product Normalization.
    N(x) = (x . B_C5) / ||B_C5||^2
    Here, we simulate this by projecting numeric values onto a C5 basis vector [1, 1, 1, 1, 1].
    """
    if not check_circuit_breaker():
        return jsonify({"error": "Service Unavailable (Circuit Breaker)"}), 503

    start_time = time.time()
    try:
        data = request.get_json()
        if not data or 'telemetry' not in data:
             return jsonify({"error": "Invalid input: missing 'telemetry' vector"}), 400

        vector = data['telemetry'] # Expected list of numbers
        if not isinstance(vector, list):
             return jsonify({"error": "Telemetry must be a list"}), 400

        # C5 Basis: 5 dimensions, unity
        basis = [1, 1, 1, 1, 1]

        # Pad or truncate vector to 5 dimensions
        vec_5 = (vector + [0]*5)[:5]

        # Dot Product
        dot_product = sum(v * b for v, b in zip(vec_5, basis))
        magnitude_sq = sum(b**2 for b in basis) # 5

        normalized_scalar = dot_product / magnitude_sq

        duration = (time.time() - start_time) * 1000
        audit_log("VEHICLE_MCP_NORMALIZE", "PASS", {
            "tool": "vehicle_normalize_data",
            "output_hash": hashlib.sha256(str(normalized_scalar).encode()).hexdigest(),
            "duration_ms": duration
        })

        REQUEST_COUNT.labels('POST', '/vehicle_normalize_data', '200').inc()
        return jsonify({"normalized_value": normalized_scalar, "basis": "C5"}), 200

    except Exception as e:
        trip_circuit_breaker()
        REQUEST_COUNT.labels('POST', '/vehicle_normalize_data', '500').inc()
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
