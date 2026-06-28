"""Sequential replication runner.

Runs N replications one after another, generating seeds from the
base simulation config internally.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from loguru import logger

from src.simulation._config import SimulationConfig
from src.simulation._types import SimulationResult
from src.simulation.engine import SimulationEngine
from src.simulation.generators import EmpiricalArrival, EmpiricalService


def run_replications(
    interarrivals: np.ndarray,
    service_times: np.ndarray,
    sim_config: SimulationConfig,
    n_replications: int,
) -> list[SimulationResult]:
    """Run N replications sequentially.

    Args:
        interarrivals: Scaled inter-arrival times.
        service_times: Service times.
        sim_config: Base simulation configuration.
        n_replications: Number of replications to run.

    Returns:
        List of simulation results, one per replication.
    """
    results: list[SimulationResult] = []
    for i in range(n_replications):
        seed = sim_config.seed + i
        cfg = replace(sim_config, seed=seed)
        arrival = EmpiricalArrival(interarrivals)
        service = EmpiricalService(service_times)
        r = SimulationEngine(arrival, service, cfg).run()
        results.append(r)

    logger.info(f"Replications: {len(results)}/{n_replications} completed")
    return results
