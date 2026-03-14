"""Signal-derived economics helpers for BlackMamba task estimation."""

from __future__ import annotations

from dataclasses import asdict, dataclass


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(slots=True)
class BudgetSignals:
    """Normalized estimation inputs."""

    complexity: float = 0.5
    risk: float = 0.35
    interface_count: int = 1
    checkpoint_count: int = 1
    dependency_count: int = 0
    reward_alignment: float = 0.8

    def normalized(self) -> "BudgetSignals":
        return BudgetSignals(
            complexity=_clamp(self.complexity),
            risk=_clamp(self.risk),
            interface_count=max(1, int(self.interface_count)),
            checkpoint_count=max(0, int(self.checkpoint_count)),
            dependency_count=max(0, int(self.dependency_count)),
            reward_alignment=_clamp(self.reward_alignment),
        )

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self.normalized())


@dataclass(slots=True)
class CostEstimate:
    """Deterministic task-cost output."""

    predicted_tokens: int
    predicted_minutes: float
    predicted_cost_usd: float
    signals: BudgetSignals

    def to_dict(self) -> dict[str, float | int | dict[str, float | int]]:
        return {
            "predicted_tokens": self.predicted_tokens,
            "predicted_minutes": self.predicted_minutes,
            "predicted_cost_usd": self.predicted_cost_usd,
            "signals": self.signals.to_dict(),
        }


class SignalEconomicsModel:
    """Deterministic token/time/cost model calibrated from XML coefficients."""

    def __init__(
        self,
        *,
        base_tokens: int = 48000,
        base_minutes: float = 42.0,
        base_token_rate: float = 0.000035,
        base_minute_rate: float = 0.42,
        approval_penalty_minutes: float = 3.0,
        risk_multiplier: float = 0.65,
        interface_multiplier: float = 0.12,
        dependency_multiplier: float = 0.07,
        checkpoint_penalty_tokens: int = 1200,
    ) -> None:
        self.base_tokens = int(base_tokens)
        self.base_minutes = float(base_minutes)
        self.base_token_rate = float(base_token_rate)
        self.base_minute_rate = float(base_minute_rate)
        self.approval_penalty_minutes = float(approval_penalty_minutes)
        self.risk_multiplier = float(risk_multiplier)
        self.interface_multiplier = float(interface_multiplier)
        self.dependency_multiplier = float(dependency_multiplier)
        self.checkpoint_penalty_tokens = int(checkpoint_penalty_tokens)

    @classmethod
    def from_config(cls, config: dict[str, float | int]) -> "SignalEconomicsModel":
        return cls(
            base_tokens=int(config.get("base_tokens", 48000)),
            base_minutes=float(config.get("base_minutes", 42.0)),
            base_token_rate=float(config.get("base_token_rate", 0.000035)),
            base_minute_rate=float(config.get("base_minute_rate", 0.42)),
            approval_penalty_minutes=float(config.get("approval_penalty_minutes", 3.0)),
            risk_multiplier=float(config.get("risk_multiplier", 0.65)),
            interface_multiplier=float(config.get("interface_multiplier", 0.12)),
            dependency_multiplier=float(config.get("dependency_multiplier", 0.07)),
            checkpoint_penalty_tokens=int(config.get("checkpoint_penalty_tokens", 1200)),
        )

    def estimate(self, signals: BudgetSignals) -> CostEstimate:
        normalized = signals.normalized()

        complexity_factor = 0.7 + (normalized.complexity * 1.65)
        risk_factor = 1.0 + (normalized.risk * self.risk_multiplier)
        interface_factor = 1.0 + ((normalized.interface_count - 1) * self.interface_multiplier)
        dependency_factor = 1.0 + (normalized.dependency_count * self.dependency_multiplier)
        reward_factor = 1.0 + ((1.0 - normalized.reward_alignment) * 0.25)

        predicted_tokens = int(
            round(
                (self.base_tokens * complexity_factor * risk_factor * interface_factor * dependency_factor)
                + (normalized.checkpoint_count * self.checkpoint_penalty_tokens)
            )
        )
        predicted_minutes = round(
            (
                self.base_minutes
                * complexity_factor
                * (1.0 + (normalized.risk * 0.4))
                * (1.0 + ((normalized.interface_count - 1) * 0.08))
                * reward_factor
            )
            + (normalized.checkpoint_count * self.approval_penalty_minutes),
            2,
        )
        predicted_cost = round(
            (predicted_tokens * self.base_token_rate) + (predicted_minutes * self.base_minute_rate),
            2,
        )

        return CostEstimate(
            predicted_tokens=predicted_tokens,
            predicted_minutes=predicted_minutes,
            predicted_cost_usd=predicted_cost,
            signals=normalized,
        )
