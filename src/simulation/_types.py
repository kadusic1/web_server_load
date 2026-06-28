"""Shared dataclasses for the simulation engine layer.

Separated from ``__init__.py`` to avoid circular imports between
``__init__.py`` and the submodules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationResult:
    """Output contract between the simulation engine and Issue 4.

    Attributes:
        lambda_: Arrival rate (req/sec).
        mu: Service rate (req/sec).
        servers: Number of parallel servers.
        seed: RNG seed used for the run.
        avg_wait: Average time a request spends waiting (sec).
        avg_queue_length: Average number of requests in queue.
        server_utilization: Fraction of time servers were busy (0-1).
        total_requests: Total requests processed in the simulation.
    """

    lambda_: float
    mu: float
    servers: int
    seed: int
    avg_wait: float
    avg_queue_length: float
    server_utilization: float
    total_requests: int
    waits: tuple[float, ...] = ()
