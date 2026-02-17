"""
Model downloading utilities for Nvidia foundation models and trained agents.

Handles on-demand downloading from Hugging Face Hub to avoid repository bloat.
"""

import os
import yaml
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def load_model_manifest() -> dict:
    """
    Load the model manifest configuration.

    Returns:
        Dictionary containing model configuration

    Raises:
        FileNotFoundError: If manifest.yaml is missing
        ValueError: If manifest YAML is invalid
    """
    manifest_path = Path(__file__).parent / "manifest.yaml"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Model manifest not found at {manifest_path}. "
            f"Please ensure models/nvidia/manifest.yaml exists with model configuration."
        )

    try:
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)

        # Validate manifest structure
        _validate_manifest_structure(manifest)
        return manifest
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in manifest.yaml: {e}")


def _validate_manifest_structure(manifest: dict) -> None:
    """
    Validate that manifest has required structure.

    Raises:
        ValueError: If manifest is missing required sections or fields
    """
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a dictionary")

    required_sections = ['nvidia_foundation_models', 'trained_models']
    for section in required_sections:
        if section not in manifest:
            raise ValueError(f"Manifest missing required section: {section}")

        if not isinstance(manifest[section], dict):
            raise ValueError(f"Manifest section '{section}' must be a dictionary")

        # Validate each model has required fields
        for model_key, model_config in manifest[section].items():
            if not isinstance(model_config, dict):
                raise ValueError(
                    f"Model '{model_key}' in '{section}' must have a dict configuration"
                )

            if section == 'nvidia_foundation_models':
                if 'huggingface_id' not in model_config:
                    raise ValueError(
                        f"Foundation model '{model_key}' missing required field: huggingface_id"
                    )
            elif section == 'trained_models':
                if 'local_cache' not in model_config:
                    raise ValueError(
                        f"Trained model '{model_key}' missing required field: local_cache"
                    )



def download_foundation_model(
    model_key: str,
    cache_dir: Optional[str] = None,
    resume: bool = True,
    verify: bool = True
) -> str:
    """
    Download Nvidia foundation model from Hugging Face Hub on-demand.

    Args:
        model_key: Key in manifest (e.g., 'llama2_7b', 'megatron_gpt')
        cache_dir: Override cache directory
        resume: Resume download if interrupted
        verify: Verify checksums

    Returns:
        Path to downloaded model
    """
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise ImportError("Install huggingface_hub: pip install huggingface_hub")

    manifest = load_model_manifest()

    if model_key not in manifest['nvidia_foundation_models']:
        available = list(manifest['nvidia_foundation_models'].keys())
        raise ValueError(f"Model '{model_key}' not found. Available: {available}")

    model_config = manifest['nvidia_foundation_models'][model_key]
    target_cache = cache_dir or model_config['local_cache']

    logger.info(f"Downloading {model_config['huggingface_id']} to {target_cache}")

    model_path = snapshot_download(
        repo_id=model_config['huggingface_id'],
        cache_dir=target_cache,
        resume_download=resume,
        local_dir_use_symlinks=True
    )

    logger.info(f"Successfully downloaded to {model_path}")
    return model_path


def download_trained_model(
    model_key: str,
    cache_dir: Optional[str] = None,
    use_s3: bool = False
) -> str:
    """
    Download trained vehicle agent model.

    Args:
        model_key: Key in manifest (e.g., 'vehicle_agent_v1_0')
        cache_dir: Override local cache directory
        use_s3: Download from S3 instead of local filesystem

    Returns:
        Path to model weights
    """
    manifest = load_model_manifest()

    if model_key not in manifest['trained_models']:
        available = list(manifest['trained_models'].keys())
        raise ValueError(f"Trained model '{model_key}' not found. Available: {available}")

    model_config = manifest['trained_models'][model_key]
    target_cache = cache_dir or model_config['local_cache']

    if use_s3:
        return _download_from_s3(model_key, model_config, target_cache)
    else:
        return _load_local_model(model_key, target_cache)


def _download_from_s3(model_key: str, model_config: dict, target_cache: str) -> str:
    """Download trained model from S3 bucket."""
    try:
        import boto3
    except ImportError:
        raise ImportError("Install boto3 for S3 support: pip install boto3")

    os.makedirs(target_cache, exist_ok=True)

    s3 = boto3.client('s3')
    bucket = 'adaptco-models'

    # Extract bucket and key from URL
    weights_url = model_config['weights_url']
    # s3://bucket/path/to/file -> extract bucket and key
    s3_path = weights_url.replace('s3://', '')

    try:
        bucket_name, key = s3_path.split('/', 1)
        local_path = os.path.join(target_cache, os.path.basename(key))

        logger.info(f"Downloading {weights_url} from S3...")
        s3.download_file(bucket_name, key, local_path)
        logger.info(f"Downloaded to {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Failed to download from S3: {e}")
        raise


def _load_local_model(model_key: str, target_cache: str) -> str:
    """Load trained model from local cache."""
    model_weights = os.path.join(target_cache, "model.safetensors")

    if not os.path.exists(model_weights):
        raise FileNotFoundError(
            f"Model weights not found at {model_weights}. "
            f"Train the model first using mlops/train_vehicle_agents.py"
        )

    logger.info(f"Loaded {model_key} from {model_weights}")
    return model_weights


def get_model_metadata(model_key: str) -> dict:
    """Get metadata for a trained model."""
    manifest = load_model_manifest()

    if model_key not in manifest['trained_models']:
        raise ValueError(f"Model '{model_key}' not found in manifest")

    return manifest['trained_models'][model_key]


def list_available_models() -> dict:
    """List all available foundation and trained models."""
    manifest = load_model_manifest()
    return {
        "foundation_models": list(manifest['nvidia_foundation_models'].keys()),
        "trained_models": list(manifest['trained_models'].keys())
    }


if __name__ == "__main__":
    import sys

    # CLI interface for downloading models
    if len(sys.argv) > 1:
        model_to_download = sys.argv[1]

        try:
            path = download_foundation_model(model_to_download)
            print(f"Successfully downloaded: {path}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        available = list_available_models()
        print("Available models:")
        print(f"Foundation: {available['foundation_models']}")
        print(f"Trained: {available['trained_models']}")
