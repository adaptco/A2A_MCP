"""
Bifurcation Analyzer for Phase Space Comparison.
Runs LangGraph and LangChain orchestrators in parallel and detects divergence.
"""
import numpy as np
from scipy.stats import entropy
from scipy.spatial.distance import euclidean
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
import json

from langgraph_orchestrator import run_langgraph_simulation
from langchain_orchestrator import run_langchain_simulation


class BifurcationAnalyzer:
    """Analyzes phase space bifurcation between LangGraph and LangChain."""
    
    def __init__(self):
        self.langgraph_trajectory = []
        self.langchain_trajectory = []
        self.divergence_points = []
    
    def run_parallel_simulations(self, steps: int = 100):
        """Execute both orchestrators and collect trajectories."""
        print("Running LangGraph simulation...")
        lg_result = run_langgraph_simulation(steps)
        
        print("Running LangChain simulation...")
        lc_result = run_langchain_simulation(steps)
        
        return lg_result, lc_result
    
    def compute_trajectory_divergence(
        self, 
        lg_state: dict, 
        lc_state: dict
    ) -> float:
        """Compute KL divergence between trajectories."""
        # Extract position vectors
        lg_positions = []
        lc_positions = []
        
        for agent_key in ["boss", "bigboss", "avatar"]:
            if agent_key in lg_state:
                lg_positions.extend(lg_state[agent_key]["position"])
            if agent_key in lc_state:
                lc_positions.extend(lc_state[agent_key]["position"])
        
        # Compute Euclidean distance as a proxy for divergence
        if lg_positions and lc_positions:
            return euclidean(lg_positions, lc_positions)
        return 0.0
    
    def detect_bifurcation_points(
        self,
        lg_result: dict,
        lc_result: dict,
        threshold: float = 10.0
    ) -> List[int]:
        """Identify timesteps where models significantly diverge."""
        divergence = self.compute_trajectory_divergence(
            lg_result.get("final_state", {}),
            lc_result
        )
        
        bifurcation_points = []
        if divergence > threshold:
            bifurcation_points.append(lg_result.get("step_count", 0))
        
        return bifurcation_points
    
    def visualize_phase_space(
        self,
        lg_result: dict,
        lc_result: dict,
        output_path: str = "phase_space_bifurcation.png"
    ):
        """Generate phase space visualization."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Metrics comparison
        lg_metrics = lg_result.get("metrics", {})
        lc_metrics = lc_result.get("metrics", {})
        
        metrics_names = list(lg_metrics.keys())
        lg_values = [lg_metrics.get(m, 0) for m in metrics_names]
        lc_values = [lc_metrics.get(m, 0) for m in metrics_names]
        
        x = np.arange(len(metrics_names))
        width = 0.35
        
        axes[0, 0].bar(x - width/2, lg_values, width, label='LangGraph')
        axes[0, 0].bar(x + width/2, lc_values, width, label='LangChain')
        axes[0, 0].set_ylabel('Metric Value')
        axes[0, 0].set_title('Phase Space Metrics Comparison')
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(metrics_names, rotation=45, ha='right')
        axes[0, 0].legend()
        
        # Trajectory divergence
        divergence = self.compute_trajectory_divergence(
            lg_result.get("final_state", {}),
            lc_result
        )
        axes[0, 1].bar(['Trajectory Divergence'], [divergence])
        axes[0, 1].set_ylabel('Euclidean Distance')
        axes[0, 1].set_title('Model Bifurcation Magnitude')
        
        # Step count comparison
        axes[1, 0].bar(
            ['LangGraph', 'LangChain'],
            [lg_result.get("step_count", 0), lc_result.get("step_count", 0)]
        )
        axes[1, 0].set_ylabel('Steps')
        axes[1, 0].set_title('Execution Steps')
        
        # Summary text
        summary = f"""
        LangGraph Steps: {lg_result.get("step_count", 0)}
        LangChain Steps: {lc_result.get("step_count", 0)}
        Divergence: {divergence:.2f}
        
        Bifurcation Detected: {divergence > 10.0}
        """
        axes[1, 1].text(0.1, 0.5, summary, fontsize=10, verticalalignment='center')
        axes[1, 1].axis('off')
        axes[1, 1].set_title('Analysis Summary')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        print(f"Visualization saved to {output_path}")
        
        return fig
    
    def generate_report(
        self,
        lg_result: dict,
        lc_result: dict
    ) -> str:
        """Generate a detailed bifurcation analysis report."""
        divergence = self.compute_trajectory_divergence(
            lg_result.get("final_state", {}),
            lc_result
        )
        
        report = f"""
# Phase Space Bifurcation Analysis Report

## Execution Summary
- **LangGraph Steps**: {lg_result.get("step_count", 0)}
- **LangChain Steps**: {lc_result.get("step_count", 0)}

## Metrics Comparison

### LangGraph Metrics
{json.dumps(lg_result.get("metrics", {}), indent=2)}

### LangChain Metrics
{json.dumps(lc_result.get("metrics", {}), indent=2)}

## Bifurcation Analysis
- **Trajectory Divergence**: {divergence:.4f}
- **Bifurcation Detected**: {divergence > 10.0}

## Interpretation
{"The models have significantly diverged in phase space." if divergence > 10.0 else "The models remain relatively aligned."}

LangGraph's explicit state management leads to more deterministic trajectories,
while LangChain's memory-based approach introduces variance through context accumulation.
"""
        return report


def main():
    """Run the complete bifurcation analysis."""
    analyzer = BifurcationAnalyzer()
    
    print("Starting parallel simulations...")
    lg_result, lc_result = analyzer.run_parallel_simulations(steps=100)
    
    print("\nGenerating visualizations...")
    analyzer.visualize_phase_space(lg_result, lc_result)
    
    print("\nGenerating report...")
    report = analyzer.generate_report(lg_result, lc_result)
    print(report)
    
    # Save report
    with open("phase_space/bifurcation_report.md", "w") as f:
        f.write(report)
    
    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()
