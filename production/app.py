import time

circuit_open = False
circuit_failures = 0
circuit_open_time = 0

def check_circuit():
    global circuit_failures, circuit_open_time, circuit_open
    if circuit_open:
        if time.time() - circuit_open_time > 60:
            circuit_open = False
            circuit_failures = 0
    return circuit_failures
