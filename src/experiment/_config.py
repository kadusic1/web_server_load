"""Experiment configuration and output contract dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.simulation._config import SimulationConfig


@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for the load-sweep experiment.

    Attributes:
        simulation: Base simulation parameters.
        n_replications: Number of replications per load level.
        n_rho_points: Number of utilisation (rho) levels to sweep.
        rho_min: Minimum target utilisation.
        rho_max: Maximum target utilisation.
        master_seed: Master RNG seed for reproducibility.
        interarrivals_path: Path to empirical inter-arrival times
            (.npy).
        service_sizes_path: Path to empirical service sizes (.npy).
        output_path: Path for experiment results JSON.
    """

    simulation: SimulationConfig = field(
        default_factory=SimulationConfig,
    )
    n_replications: int = 30
    n_rho_points: int = 15
    rho_min: float = 0.1
    rho_max: float = 1.5
    master_seed: int = 42
    interarrivals_path: str = "data/empirical_interarrivals.npy"
    service_sizes_path: str = "data/empirical_service_sizes.npy"
    output_path: str = "data/experiment_results.json"


@dataclass(frozen=True)
class LoadLevelRow:
    """One row of the experiment output table.

    Attributes:
        rho: Target utilisation.
        rho_actual: Measured utilisation from simulation.
        mean_wait: Mean queue wait time (seconds).
        ci_lower: Lower 95 % confidence interval bound.
        ci_upper: Upper 95 % confidence interval bound.
        p50_wait: Median wait time (seconds).
        p95_wait: 95th percentile wait time (seconds).
        p99_wait: 99th percentile wait time (seconds).
        n_replications: Number of successful replications.
    """

    rho: float
    rho_actual: float
    mean_wait: float
    ci_lower: float
    ci_upper: float
    p50_wait: float
    p95_wait: float
    p99_wait: float
    n_replications: int


@dataclass(frozen=True)
class ExperimentResult:
    """Full experiment result, one row per load level.

    Attributes:
        rows: One ``LoadLevelRow`` per rho level.
    """

    rows: list[LoadLevelRow]
