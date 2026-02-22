import os

def get_vertex_ai_model_dir():
    """
    Retrieves the authoritative directory for model artifacts.
    Vertex AI sets this to a gs:// path during custom training jobs.
    """
    # Fallback to local exports for debugging in Cloud Shell
    model_dir = os.environ.get('AIP_MODEL_DIR', './exports/v10_alpha/')
    
    # Ensure the directory exists if it's a local path
    if not model_dir.startswith('gs://'):
        os.makedirs(model_dir, exist_ok=True)
        
    print(f"--- Model Persistence Layer Active ---")
    print(f"Artifact Destination: {model_dir}")
    print(f"--------------------------------------")
    
    return model_dir