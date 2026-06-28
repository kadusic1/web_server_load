"""Simulation configuration dataclass.

Centralises all numeric simulation parameters that were previously
scattered as hardcoded defaults across ``main.py``, ``engine.py``,
and ``generators.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    servers: int = 1
    sim_time: float = 1_000_000.0
    warmup: float = 5_000.0
    seed: int = 42
    monitor_interval: float = 0.1
    bandwidth: float = 500_000
    interarrivals_path: str = "data/empirical_interarrivals.npy"
    service_sizes_path: str = "data/empirical_service_sizes.npy"
