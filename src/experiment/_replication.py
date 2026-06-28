"""Parallel replication runner.

Runs N replications using a process pool, generating seeds from the
base simulation config internally.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np
from loguru import logger

from src.simulation._config import SimulationConfig
from src.simulation._types import SimulationResult
from src.simulation.engine import SimulationEngine
from src.simulation.generators import EmpiricalArrival, EmpiricalService


def _run_one_replication(args: tuple) -> SimulationResult:
    """Run a single replication in a worker process.

    Args:
        args: (interarrivals, service_times, sim_config, seed).

    Returns:
        Simulation result for this replication.
    """
    interarrivals, service_times, sim_config, seed = args
    cfg = replace(sim_config, seed=seed)
    arrival = EmpiricalArrival(interarrivals)
    service = EmpiricalService(service_times)
    return SimulationEngine(arrival, service, cfg).run()


def run_replications(
    interarrivals: np.ndarray,
    service_times: np.ndarray,
    sim_config: SimulationConfig,
    n_replications: int,
) -> list[SimulationResult]:
    """Run N replications in parallel using a process pool.

    Args:
        interarrivals: Scaled inter-arrival times.
        service_times: Service times.
        sim_config: Base simulation configuration.
        n_replications: Number of replications to run.

    Returns:
        List of simulation results, one per replication.
    """
    tasks = [
        (interarrivals, service_times, sim_config, sim_config.seed + i)
        for i in range(n_replications)
    ]

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        results: list[SimulationResult] = list(
            ex.map(_run_one_replication, tasks),
        )

    logger.info(f"Replications: {len(results)}/{n_replications} completed")
    return results
