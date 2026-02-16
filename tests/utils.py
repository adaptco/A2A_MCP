def run_standard_flow(machine):
    """Executes a standard state transition sequence for testing."""
    machine.trigger("initialize")
    machine.trigger("validate")
    machine.trigger("execute")
