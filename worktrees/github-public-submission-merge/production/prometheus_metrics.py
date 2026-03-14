from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('vehicle_mcp_requests_total', 'Total request count', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('vehicle_mcp_request_latency_seconds', 'Request latency', ['endpoint'])
CIRCUIT_BREAKER_STATE = Gauge('vehicle_mcp_circuit_breaker_open', 'Circuit breaker state (1=Open, 0=Closed)')
VALIDATION_ERRORS = Counter('vehicle_mcp_validation_errors_total', 'Total validation errors')
