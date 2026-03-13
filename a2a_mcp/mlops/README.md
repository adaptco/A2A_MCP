# MLOps: Vehicle Agent Training Pipeline

This directory contains the MLOps infrastructure for training autonomous vehicle navigation agents using Nvidia foundation models.

## Overview

The pipeline implements transfer learning to fine-tune Nvidia foundation models (Llama 2, Megatron-GPT) on vehicle driving observation data, creating intelligent agents that can:

- Process real-time vehicle state observations
- Make steering, acceleration, and braking decisions
- Navigate safely through complex driving scenarios
- Embed themselves as autonomous agents in the A2A orchestrator

## Architecture

```
Nvidia Foundation Models (Downloaded on-demand)
        ↓
Fine-tuning on Driving Data (MLOps Pipeline)
        ↓
Trained Vehicle Agents (Versioned & Exported)
        ↓
A2A Orchestrator Integration (TrainedVehicleAgent)
```

## Quick Start

### 1. Download Foundation Model

```bash
python models/nvidia/downloading/fetch_nvidia_models.py megatron_gpt
```

### 2. Train Vehicle Agent

```bash
python mlops/train_vehicle_agents.py --version v1.0 --epochs 100 --export
```

### 3. Deploy as Agent

```python
from agents.trained_model_agent import TrainedVehicleAgent

agent = TrainedVehicleAgent(model_version="1.0")

# Use in A2A orchestrator
result = await agent.analyze_driving_scenario(observation)
```

## Directory Structure

```
mlops/
├── __init__.py
├── mlops_config.yaml              # Training configuration
├── train_vehicle_agents.py        # Training pipeline
├── evaluate.py                    # Model evaluation
└── export_agent.py               # Agent export script

models/
├── nvidia/
│   ├── manifest.yaml              # Model URLs & metadata
│   ├── downloading/
│   │   └── fetch_nvidia_models.py # Download utilities
│   └── cache/                     # Downloaded models (git-ignored)
└── trained/
    ├── vehicle_agent_v1.0/
    │   ├── model.safetensors
    │   ├── metadata.json
    │   └── config.json
    └── .gitignore
```

## Configuration

Edit `mlops/mlops_config.yaml` to customize:

```yaml
training:
  epochs: 100
  batch_size: 32
  learning_rate: 0.0001

data:
  training_data_source: "local"  # "local", "s3", "huggingface"
  synthetic_data:
    enabled: true
    num_samples: 1000

export:
  format: "safetensors"
  deployment_targets:
    - s3
    - local
```

## Training Process

### Step 1: Load Foundation Model

```python
from models.nvidia.downloading.fetch_nvidia_models import download_foundation_model

model_path = download_foundation_model("megatron_gpt")
```

### Step 2: Train on Driving Data

```python
from mlops.train_vehicle_agents import VehicleAgentTrainer

trainer = VehicleAgentTrainer(model_version="v1.0")
trainer.train(num_epochs=100)
```

### Step 3: Export as Agent

```python
export_dir = trainer.export_agent(version="v1.0", format="safetensors")
print(f"Model exported to {export_dir}")
```

### Step 4: Deploy in Orchestrator

```python
from agents.trained_model_agent import TrainedVehicleAgent
from orchestrator import MCPHub

agent = TrainedVehicleAgent(model_version="1.0")
# Agent is now ready to be used in the orchestrator pipeline
```

## Integration with A2A Orchestrator

The trained vehicle agents integrate seamlessly with the orchestrator kernel:

```python
# In your orchestrator workflow
from agents.trained_model_agent import TrainedVehicleAgent
from orchestrator.intent_engine import IntentEngine

# Create trained agent
vehicle_agent = TrainedVehicleAgent(model_version="1.0")

# Use in pipeline
async def autonomous_navigation_phase(observation):
    decision = await vehicle_agent.analyze_driving_scenario(observation)
    return decision
```

## Model Versioning

Models are versioned and tracked:

- **v1.0**: Initial training on synthetic data
- **v1.1**: Improved accuracy with 150 epochs
- **v2.0**: Transfer from larger foundation model

Each version has metadata:
```json
{
  "model_version": "v1.0",
  "training_date": "2026-02-12",
  "epochs": 100,
  "learning_rate": 0.0001,
  "best_validation_loss": 0.0234
}
```

## Storage Strategy

- **Foundation models**: Downloaded on-demand from Hugging Face
- **Trained models**: Stored locally with git-ignored binaries
- **Metadata**: Versioned in git for reproducibility
- **Weights**: Can be uploaded to S3 for CDN distribution

## Dependencies

```bash
pip install torch transformers huggingface-hub safetensors boto3
```

## Monitoring & Metrics

Training metrics are tracked:

```
Epoch 1/100 - Train Loss: 0.3456, Val Loss: 0.3210
Epoch 10/100 - Train Loss: 0.2134, Val Loss: 0.2089
...
Training completed. Best validation loss: 0.0156
```

## Troubleshooting

### Model Download Issues
```bash
# Check available models
python models/nvidia/downloading/fetch_nvidia_models.py
```

### CUDA Out of Memory
```bash
# Reduce batch size in config
batch_size: 16  # Lower than default 32
```

### Export Format Issues
```bash
# Ensure safetensors is installed
pip install safetensors
```

## Advanced: Custom Training Data

To use your own driving data:

```python
# Prepare your data
from torch.utils.data import DataLoader

custom_loader = DataLoader(your_driving_data, batch_size=32)

# Train with custom data
trainer = VehicleAgentTrainer()
trainer.train_with_custom_data(custom_loader, num_epochs=100)
```

## References

- [Nvidia Foundation Models](https://huggingface.co/nvidia)
- [Hugging Face Model Hub](https://huggingface.co/models)
- [PyTorch LSTM Documentation](https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html)

---

**Status**: Production-ready
**Last Updated**: 2026-02-12
**Maintainer**: Autonomous Vehicles Team

## Unity Autonomous Training

A Unity-focused orchestration module is available at `mlops_unity_pipeline.py` with setup instructions in `UNITY_MLOPS_SETUP.md`. It supports:

- LLM-driven Unity C# scaffold generation
- Unity environment build stage hooks
- Offline/online RL training stage hooks (ML-Agents compatible)
- Optional Vertex AI registration metadata output
- Cron-based scheduling for continuous training

