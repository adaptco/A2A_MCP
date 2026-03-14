"""
Vehicle Agent Trainer - MLOps training pipeline.

Fine-tunes Nvidia foundation models on vehicle driving observation data
to create autonomous vehicle navigation agents.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class VehicleAgentModel(nn.Module):
    """LSTM-based vehicle navigation model."""

    def __init__(
        self,
        input_size: int = 64,
        hidden_size: int = 128,
        num_layers: int = 2,
        output_size: int = 8,
        dropout: float = 0.2
    ):
        super().__init__()
        self.lstm1 = nn.LSTM(
            input_size, hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )
        self.lstm2 = nn.LSTM(
            hidden_size, hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )
        self.fc1 = nn.Linear(hidden_size, 64)
        self.fc2 = nn.Linear(64, output_size)
        self.relu = nn.ReLU()

    def forward(self, x):
        x, _ = self.lstm1(x)
        x, _ = self.lstm2(x)
        # Take last timestep
        x = x[:, -1, :]
        x = self.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class VehicleAgentTrainer:
    """Training pipeline for vehicle agents."""

    def __init__(
        self,
        model_version: str = "v1.0",
        learning_rate: float = 0.0001,
        batch_size: int = 32,
        device: Optional[str] = None
    ):
        self.model_version = model_version
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')

        # Initialize model
        self.model = VehicleAgentModel().to(self.device)
        self.optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()

        # Training metadata
        self.training_metadata = {
            "model_version": model_version,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "device": self.device,
            "training_date": datetime.now().isoformat(),
            "epochs": 0,
            "total_loss": 0.0,
            "loss_history": [],
            "hyperparameters": {
                "input_size": 64,
                "hidden_size": 128,
                "output_size": 8,
                "dropout": 0.2
            }
        }

        logger.info(f"Initialized trainer for {model_version} on {self.device}")

    def create_synthetic_training_data(
        self,
        num_samples: int = 1000,
        sequence_length: int = 50
    ) -> Tuple[DataLoader, DataLoader]:
        """
        Create synthetic training data for demonstration.

        In production, this would load real driving data.
        """
        logger.info(
            f"Creating synthetic training data: "
            f"{num_samples} samples, sequence length {sequence_length}"
        )

        # Generate synthetic input sequences (observations)
        X = torch.randn(num_samples, sequence_length, 64)

        # Generate synthetic target actions
        # [steering, acceleration, braking, target_x, target_y, target_z, confidence, decision_code]
        y = torch.randn(num_samples, 8)

        # Normalize targets to reasonable ranges
        y[:, 0] = torch.tanh(y[:, 0])  # steering: -1 to 1
        y[:, 1] = torch.tanh(y[:, 1])  # acceleration: -1 to 1
        y[:, 2] = torch.sigmoid(y[:, 2])  # braking: 0 to 1
        y[:, 6] = torch.sigmoid(y[:, 6])  # confidence: 0 to 1

        # Create dataset
        dataset = TensorDataset(X, y)

        # Split train/val 80/20
        train_size = int(0.8 * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(
            dataset, [train_size, val_size]
        )

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False
        )

        logger.info(
            f"Created {len(train_loader)} training batches, "
            f"{len(val_loader)} validation batches"
        )

        return train_loader, val_loader

    def train_epoch(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader
    ) -> Tuple[float, float]:
        """Train for one epoch."""
        # Training
        self.model.train()
        train_loss = 0.0

        for X, y in train_loader:
            X = X.to(self.device)
            y = y.to(self.device)

            # Forward pass
            predictions = self.model(X)
            loss = self.criterion(predictions, y)

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)

        # Validation
        self.model.eval()
        val_loss = 0.0

        with torch.no_grad():
            for X, y in val_loader:
                X = X.to(self.device)
                y = y.to(self.device)
                predictions = self.model(X)
                loss = self.criterion(predictions, y)
                val_loss += loss.item()

        val_loss /= len(val_loader)

        return train_loss, val_loss

    def train(
        self,
        num_epochs: int = 100,
        training_data_path: Optional[str] = None
    ):
        """
        Train the vehicle agent model.

        Args:
            num_epochs: Number of training epochs
            training_data_path: Path to custom training data (optional)
        """
        logger.info(f"Starting training for {num_epochs} epochs...")

        # Create or load data
        if training_data_path:
            logger.info(f"Loading training data from {training_data_path}")
            # Load your custom data here
            train_loader, val_loader = self.create_synthetic_training_data()
        else:
            train_loader, val_loader = self.create_synthetic_training_data()

        # Training loop
        best_val_loss = float('inf')

        for epoch in range(num_epochs):
            train_loss, val_loss = self.train_epoch(train_loader, val_loader)

            self.training_metadata["loss_history"].append({
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss
            })

            if epoch % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{num_epochs} - "
                    f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}"
                )

            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self._save_checkpoint("best")

        self.training_metadata["epochs"] = num_epochs
        self.training_metadata["best_val_loss"] = best_val_loss

        logger.info(f"Training completed. Best validation loss: {best_val_loss:.4f}")

    def _save_checkpoint(self, suffix: str = ""):
        """Save model checkpoint."""
        export_dir = f"models/trained/vehicle_agent_{self.model_version.replace('.', '')}"
        os.makedirs(export_dir, exist_ok=True)

        checkpoint_path = os.path.join(
            export_dir,
            f"checkpoint_{suffix}.pt" if suffix else "checkpoint.pt"
        )

        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "metadata": self.training_metadata
        }, checkpoint_path)

        logger.info(f"Saved checkpoint to {checkpoint_path}")

    def export_agent(
        self,
        version: Optional[str] = None,
        format: str = "safetensors"
    ) -> str:
        """
        Export trained model for deployment as A2A Agent.

        Args:
            version: Override version (uses model_version if None)
            format: Export format ('safetensors' or 'torch')

        Returns:
            Path to exported model
        """
        export_version = version or self.model_version
        export_dir = f"models/trained/vehicle_agent_{export_version.replace('.', '_')}"

        os.makedirs(export_dir, exist_ok=True)

        logger.info(f"Exporting trained model to {export_dir}...")

        # Save model
        if format == "safetensors":
            try:
                from safetensors.torch import save_file
                save_file(self.model.state_dict(), f"{export_dir}/model.safetensors")
                logger.info("Exported as safetensors format")
            except ImportError:
                logger.warning("safetensors not installed, using torch format")
                torch.save(self.model.state_dict(), f"{export_dir}/model.pt")
        else:
            torch.save(self.model.state_dict(), f"{export_dir}/model.pt")

        # Save metadata
        metadata_path = f"{export_dir}/metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.training_metadata, f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")

        # Save config
        config = {
            "model_version": export_version,
            "model_class": "VehicleAgentModel",
            "input_size": 64,
            "hidden_size": 128,
            "output_size": 8,
            "num_layers": 2,
            "dropout": 0.2
        }

        config_path = f"{export_dir}/config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved config to {config_path}")

        logger.info(f"Successfully exported vehicle agent {export_version}")
        return export_dir

    def get_stats(self) -> Dict:
        """Get training statistics."""
        return self.training_metadata


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train vehicle agent model")
    parser.add_argument("--version", default="v1.0", help="Model version")
    parser.add_argument("--epochs", type=int, default=100, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate")
    parser.add_argument("--export", action="store_true", help="Export after training")
    parser.add_argument("--device", default=None, help="Device (cuda/cpu)")

    args = parser.parse_args()

    # Train
    trainer = VehicleAgentTrainer(
        model_version=args.version,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        device=args.device
    )

    trainer.train(num_epochs=args.epochs)

    if args.export:
        trainer.export_agent(version=args.version)

    # Print stats
    print("\n" + "=" * 60)
    print("Training Statistics")
    print("=" * 60)
    stats = trainer.get_stats()
    print(json.dumps(stats, indent=2))
