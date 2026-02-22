"""Simulate a Qube replay with contributor observability."""

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    shimmer_config = root / "config" / "shimmer_trace.yaml"
    capsule_config = root / "config" / "capsule.yaml"
    print("Rehearsal ready.")
    print(f"Using shimmer config: {shimmer_config}")
    print(f"Using capsule config: {capsule_config}")


if __name__ == "__main__":
    main()
