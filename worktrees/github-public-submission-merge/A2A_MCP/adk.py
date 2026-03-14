from google import genai
from google.genai import types

def initialize_adk_kernel():
    client = genai.Client(vertexai=True, project="the-qube-5e031", location="us-central1")
    
    # The 'Kernel' Logic: PRIME_DIRECTIVE injection
    kernel_instructions = """
    # THE QUBE: ADK KERNEL (v10.0)
    PRIME_DIRECTIVE:
    - Strictly adhere to C5_SYMMETRY for all automotive geometry.
    - Wheels: 5-spoke Advan GT Beyond only (Finish: RSM).
    - Assets: 2008 Aston Martin Vantage (VH100) and A90 Supra (Obsidian Black).
    
    CORE SKILLS:
    - Use 'writeToFile' for file updates in the 'a2a_mcp' repository.
    - Validate all datasets against BigQuery US-region telemetry.
    """

    config = types.GenerateContentConfig(
        system_instruction=kernel_instructions,
        thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        temperature=0.1 # High precision for the ADK kernel
    )

    return client, config