"""Specifications loader for Supra domain and Judge criteria."""

import yaml
<<<<<<< HEAD
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)
=======
from typing import Dict, Any, Optional
from pathlib import Path

>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

class SpecsLoader:
    """Load and cache specification files."""

    def __init__(self, specs_dir: Optional[str] = None):
        if specs_dir is None:
            specs_dir = Path(__file__).parent
        self.specs_dir = Path(specs_dir)
        self._cache: Dict[str, Any] = {}

    def load_supra_specs(self) -> Dict[str, Any]:
        """Load and cache Supra A90 specifications."""
        cache_key = "supra_specs"
        if cache_key in self._cache:
            return self._cache[cache_key]

        spec_file = self.specs_dir / "supra_specs.yaml"
<<<<<<< HEAD
        if not spec_file.exists():
            raise FileNotFoundError(
                f"Supra specs file not found at {spec_file}. "
                f"Please ensure specs/supra_specs.yaml exists."
            )

        try:
            with open(spec_file, "r") as f:
                specs = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in supra_specs.yaml: {e}")
=======
        with open(spec_file, "r") as f:
            specs = yaml.safe_load(f)
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

        self._cache[cache_key] = specs
        return specs

    def load_judge_criteria(self) -> Dict[str, Any]:
        """Load and cache Judge criteria configuration."""
        cache_key = "judge_criteria"
        if cache_key in self._cache:
            return self._cache[cache_key]

        criteria_file = self.specs_dir / "judge_criteria.yaml"
<<<<<<< HEAD
        if not criteria_file.exists():
            raise FileNotFoundError(
                f"Judge criteria file not found at {criteria_file}. "
                f"Please ensure specs/judge_criteria.yaml exists."
            )

        try:
            with open(criteria_file, "r") as f:
                criteria = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in judge_criteria.yaml: {e}")
=======
        with open(criteria_file, "r") as f:
            criteria = yaml.safe_load(f)
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

        self._cache[cache_key] = criteria
        return criteria

<<<<<<< HEAD
    def load_base44_map(self) -> Dict[str, Any]:
        """Load and cache Base44 world map configuration."""
        cache_key = "base44_map"
        if cache_key in self._cache:
            return self._cache[cache_key]

        map_file = self.specs_dir / "base44_map.yaml"
        if not map_file.exists():
            raise FileNotFoundError(
                f"Base44 map file not found at {map_file}. "
                f"Please ensure specs/base44_map.yaml exists."
            )

        try:
            with open(map_file, "r") as f:
                world_map = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in base44_map.yaml: {e}")

        self._cache[cache_key] = world_map
        return world_map

=======
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
    def get_supra_config(self) -> Dict[str, Any]:
        """Return supra section from specs."""
        specs = self.load_supra_specs()
        return specs.get("supra", {})

    def get_supra_powertrain(self) -> Dict[str, Any]:
        """Return powertrain section from specs."""
        specs = self.load_supra_specs()
        return specs.get("powertrain", {})

    def get_supra_performance(self) -> Dict[str, Any]:
        """Return performance section from specs."""
        specs = self.load_supra_specs()
        return specs.get("performance", {})

    def get_supra_constraints(self) -> Dict[str, Any]:
        """Return constraints section from specs."""
        specs = self.load_supra_specs()
        return specs.get("constraints", {})

    def get_judge_criteria_config(self) -> Dict[str, Any]:
        """Return criteria section from judge config."""
        criteria = self.load_judge_criteria()
        return criteria.get("criteria", {})

    def get_judge_weights(self) -> Dict[str, float]:
        """Extract weights for all criteria."""
        criteria = self.get_judge_criteria_config()
        return {name: cfg.get("weight", 1.0) for name, cfg in criteria.items()}

    def get_judge_preset(self, preset_name: str = "simulation") -> Dict[str, float]:
        """Get a judge tuning preset (arcade, simulation, casual)."""
        criteria = self.load_judge_criteria()
        tuning = criteria.get("tuning", {})
        presets = tuning.get("presets", {})
        preset = presets.get(preset_name, {})

        # Convert preset weights
        weights = {}
<<<<<<< HEAD
        for key in ["safety", "spec", "intent", "latency"]:
=======
        for key in ["safety", "spec_alignment", "player_intent", "latency"]:
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
            weight_key = f"{key}_weight"
            weights[key] = preset.get(weight_key, 1.0)

        return weights

    def clear_cache(self) -> None:
        """Clear the specification cache."""
        self._cache.clear()

    def __repr__(self) -> str:
        return f"<SpecsLoader specs_dir={self.specs_dir}>"


# Global singleton loader
_loader = None


def get_loader() -> SpecsLoader:
    """Access the global specs loader."""
    global _loader
    if _loader is None:
        _loader = SpecsLoader()
    return _loader
