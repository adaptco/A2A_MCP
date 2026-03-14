# Unity MLOps Setup Guide

This document outlines the steps to configure and run the autonomous Unity MLOps pipeline for RL training and model registration.

## Prerequisites
- **Unity Hub & Editor**: Version 2022.3+ recommended.
- **ML-Agents Toolkit**: Installed via pip (`pip install mlagents`).
- **Google Cloud SDK**: Authenticated with access to Vertex AI.
- **Docker**: For running the local automation stack.

## Configuration
1.  **Environment Variables**:
    Create a `.env` file from `.env.example`:
    ```bash
    VERTEX_PROJECT=your-project-id
    VERTEX_REGION=us-central1
    UNITY_EXECUTABLE=/path/to/Unity.exe
    ```

2.  **Local Automation Runtime**:
    If using the simulator for browser/desktop automations:
    ```powershell
    .\scripts\automation_runtime.ps1 -Action up -Build
    ```

## Running the Pipeline
The pipeline is orchestrated by `mlops_unity_pipeline.py`. It can be run as a single job or scheduled.

### Example: Single Training Run
```python
from mlops_unity_pipeline import UnityMLOpsOrchestrator, TrainingJob

orchestrator = UnityMLOpsOrchestrator()
job = TrainingJob(
    job_id="agent-v1-alpha",
    project_path="./unity-project",
    register_to_vertex=True
)

result = await orchestrator.execute_training_job(job)
print(f"Training completed: {result.trained_model_path}")
```

## CI/CD Integration
The pipeline is automatically triggered via GitHub Actions on changes to agent logic or environment configurations.
See `.github/workflows/ml_pipeline.yml` for details.

## Troubleshooting
- **Unity Build Failures**: Ensure the `UNITY_EXECUTABLE` path is correct and all project dependencies are resolved in the Unity Editor.
- **Vertex AI Registration**: Verify that the service account has the `Vertex AI User` role.
- **Automation Stack**: Check Docker logs if the simulator frontend (`http://localhost:4173`) is unreachable.
