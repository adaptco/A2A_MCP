"""
Trained Vehicle Agent - Wraps MLOps-trained models as A2A Agents.

This agent embeds a neural network trained on vehicle driving data as an
autonomous agent in the A2A orchestrator system.
"""

import torch
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import json

try:
    from models.nvidia.downloading.fetch_nvidia_models import download_trained_model, get_model_metadata
except ImportError:
    from .nvidia.downloading.fetch_nvidia_models import download_trained_model, get_model_metadata

logger = logging.getLogger(__name__)


class TrainedVehicleAgent:
    """
    Autonomous vehicle navigation agent powered by trained neural network.

    This agent processes vehicle environment observations and produces
    driving decisions based on a model fine-tuned on Nvidia foundation models.
    """

    def __init__(
        self,
        model_version: str = "v1.0",
        device: Optional[str] = None,
        use_s3: bool = False
    ):
        """
        Initialize the trained vehicle agent.

        Args:
            model_version: Model version (e.g., 'v1.0', 'v1.1')
            device: torch device ('cuda', 'cpu', or None for auto-detect)
            use_s3: Download from S3 if True, else from local cache
        """
        self.agent_name = f"TrainedVehicleAgent_{model_version.replace('.', '_')}"
        self.model_version = model_version
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

        # Load model metadata
        model_key = f"vehicle_agent_v{model_version.replace('.', '_')}"
        self.metadata = get_model_metadata(model_key)

        # Download or load trained model
        try:
            model_weights_path = download_trained_model(
                model_key,
                use_s3=use_s3
            )

            # Validate that model path was returned
            if not model_weights_path:
                raise FileNotFoundError(
                    f"Model weights path is None for version {model_version}. "
                    f"Please ensure the model has been trained using: "
                    f"python mlops/train_vehicle_agents.py --version {model_version} --export"
                )

            self.model = self._load_model(model_weights_path)
            self.model.to(self.device)
            self.model.eval()

            logger.info(
                f"Initialized {self.agent_name} on device {self.device}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise

        # Tracking
        self.execution_count = 0
        self.last_execution = None

    def _load_model(self, weights_path: str) -> torch.nn.Module:
        """Load model weights from file."""
        if weights_path.endswith('.safetensors'):
            try:
                from safetensors.torch import load_file
                state_dict = load_file(weights_path)
                model = self._build_model_architecture()
                model.load_state_dict(state_dict)
                return model
            except ImportError:
                logger.warning("safetensors not installed, trying torch format")

        # Fallback to torch format
        return torch.load(weights_path, map_location=self.device)

    def _build_model_architecture(self) -> torch.nn.Module:
        """Build the LSTM-based vehicle navigation model."""
        # This would be replaced with your actual architecture
        # For now, a placeholder that can be extended

        class VehicleNavigationLSTM(torch.nn.Module):
            def __init__(self, input_size=64, hidden_size=128, output_size=8):
                super().__init__()
                self.lstm1 = torch.nn.LSTM(input_size, hidden_size, batch_first=True)
                self.lstm2 = torch.nn.LSTM(hidden_size, hidden_size, batch_first=True)
                self.fc = torch.nn.Linear(hidden_size, output_size)

            def forward(self, x):
                x, _ = self.lstm1(x)
                x, _ = self.lstm2(x)
                x = self.fc(x[:, -1, :])  # Last timestep
                return x

        return VehicleNavigationLSTM()

    async def analyze_driving_scenario(
        self,
        observation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process vehicle environment observation and produce driving decision.

        Args:
            observation: Vehicle state dict containing:
                - velocity: Current speed
                - position: (x, y, z) coordinates
                - heading: Direction angle
                - road_ahead: Road conditions ahead
                - obstacles: Detected obstacles
                - traffic: Traffic signals

        Returns:
            Action dict containing:
                - steering: Steering angle (-1.0 to 1.0)
                - acceleration: Throttle (-1.0 to 1.0)
                - braking: Brake force (0.0 to 1.0)
                - confidence: Confidence score
                - decision_rationale: Explanation of decision
        """
        try:
            # Prepare input tensor
            state_tensor = self._prepare_input(observation)

            # Forward pass through model
            with torch.no_grad():
                predictions = self.model(state_tensor.to(self.device))

            # Decode predictions into driving actions
            action = self._decode_prediction(predictions, observation)

            # Track execution
            self.execution_count += 1
            self.last_execution = datetime.now().isoformat()

            return {
                "agent_name": self.agent_name,
                "model_version": self.model_version,
                "action": action,
                "observation": observation,
                "metadata": {
                    "execution_id": self.execution_count,
                    "timestamp": self.last_execution,
                    "device": self.device
                }
            }
        except Exception as e:
            logger.error(f"Error in driving decision: {e}")
            return {
                "agent_name": self.agent_name,
                "error": str(e),
                "action": {
                    "steering": 0.0,
                    "acceleration": -0.5,  # Brake
                    "braking": 1.0
                }
            }

    def _prepare_input(self, observation: Dict[str, Any]) -> torch.Tensor:
        """
        Convert raw observation to model input tensor.

        Normalizes and structures the driving data for LSTM processing.
        """
        # Extract features from observation
        velocity = observation.get('velocity', [0.0, 0.0, 0.0])
        position = observation.get('position', [0.0, 0.0, 0.0])
        heading = observation.get('heading', 0.0)
        road_data = observation.get('road_ahead', [])
        obstacles = observation.get('obstacles', [])

        # Normalize each component
        features = []

        # Velocity (3 features)
        velocity_norm = [v / 30.0 for v in velocity]  # Max 30 m/s
        features.extend(velocity_norm)

        # Position (3 features)
        position_norm = [p / 1000.0 for p in position]  # Normalize to 1km scale
        features.extend(position_norm)

        # Heading (1 feature)
        heading_norm = heading / 360.0
        features.append(heading_norm)

        # Road ahead (up to 32 features)
        road_features = road_data[:32] if road_data else [0.0] * 32
        road_features.extend([0.0] * (32 - len(road_features)))
        features.extend(road_features)

        # Obstacles (up to 16 features)
        obstacle_features = obstacles[:16] if obstacles else [0.0] * 16
        obstacle_features.extend([0.0] * (16 - len(obstacle_features)))
        features.extend(obstacle_features)

        # Convert to tensor [1, 1, feature_size] for single timestep
        tensor = torch.FloatTensor(features).unsqueeze(0).unsqueeze(0)
        return tensor

    def _decode_prediction(
        self,
        predictions: torch.Tensor,
        observation: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Decode model output tensor into driving actions.

        Output format (8 values):
        [0-2]: steering, acceleration, braking
        [3-5]: target_x, target_y, target_z
        [6-7]: confidence, decision_code

        Raises:
            ValueError: If predictions shape is invalid
        """
        # Validate tensor shape before indexing
        if predictions.dim() != 2:
            raise ValueError(
                f"Expected predictions tensor to be 2D (batch x output_size), "
                f"got shape {predictions.shape}"
            )

        if predictions.size(0) < 1:
            raise ValueError(
                f"Expected predictions batch size >= 1, got {predictions.size(0)}"
            )

        if predictions.size(1) < 8:
            raise ValueError(
                f"Expected predictions output size >= 8, "
                f"got {predictions.size(1)}"
            )

        pred_values = predictions.cpu().numpy()[0]

        steering = float(torch.tanh(predictions[0, 0]))  # -1 to 1
        acceleration = float(torch.tanh(predictions[0, 1]))  # -1 to 1
        braking = float(torch.sigmoid(predictions[0, 2]))  # 0 to 1

        confidence = float(torch.sigmoid(predictions[0, 6]))

        return {
            "steering": steering,
            "acceleration": acceleration,
            "braking": braking,
            "target_location": {
                "x": float(pred_values[3]) if len(pred_values) > 3 else 0.0,
                "y": float(pred_values[4]) if len(pred_values) > 4 else 0.0,
                "z": float(pred_values[5]) if len(pred_values) > 5 else 0.0,
            },
            "confidence": confidence,
            "decision_rationale": self._generate_rationale(steering, acceleration, braking)
        }

    def _generate_rationale(
        self,
        steering: float,
        acceleration: float,
        braking: float
    ) -> str:
        """Generate human-readable explanation of driving decision."""
        actions = []

        if abs(steering) > 0.1:
            direction = "left" if steering < 0 else "right"
            magnitude = abs(steering)
            actions.append(f"Turn {direction} ({magnitude:.1%})")

        if acceleration > 0.1:
            actions.append(f"Accelerate ({acceleration:.1%})")
        elif braking > 0.1:
            actions.append(f"Brake ({braking:.1%})")

        return " + ".join(actions) if actions else "Maintain course"

    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics."""
        return {
            "agent_name": self.agent_name,
            "model_version": self.model_version,
            "device": self.device,
            "executions": self.execution_count,
            "last_execution": self.last_execution,
            "metadata": self.metadata
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def demo():
        # Initialize agent
        agent = TrainedVehicleAgent(model_version="1.0")

        # Create sample observation
        observation = {
            "velocity": [20.0, 0.0, 0.0],  # Moving forward at 20 m/s
            "position": [100.0, 50.0, 0.0],
            "heading": 90.0,  # Facing north
            "road_ahead": [0.0] * 32,  # Clear road
            "obstacles": [],
            "traffic": "green"
        }

        # Get driving decision
        result = await agent.analyze_driving_scenario(observation)
        print(json.dumps(result, indent=2))

        # Get stats
        stats = agent.get_stats()
        print(f"\nAgent Stats: {stats}")

    asyncio.run(demo())
