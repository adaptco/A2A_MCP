def synthesize_lora_training_data(verified_nodes: list) -> list:
    """
    Converts indexed vector nodes into LoRA-compatible
    instruction-tuning format.
    """
    training_set = []
    for node in verified_nodes:
        node_type = node.get("metadata", {}).get("type", "")
        if node_type == "recovery_logic":
            prompt = f"SYSTEM: You are in a supercritical rest state. Context: {node['text']}"
            response = "ACTION: Execute self-healing protocol v2.5 while maintaining node integrity."
            training_set.append({"instruction": prompt, "output": response})
        elif node_type == "code_solution":
            prompt = f"SYSTEM: Review and improve this solution. Context: {node['text']}"
            response = "ACTION: Apply code optimization with error boundary enforcement."
            training_set.append({"instruction": prompt, "output": response})
    return training_set
