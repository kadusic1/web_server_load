"""Simulation engine layer for web server modeling.

Uses SimPy to model request arrivals, queuing, and service.
Produces the output contract for Issue 4 (Experiment Orchestration).
"""

from src.simulation._config import SimulationConfig
from src.simulation._types import SimulationResult
from src.simulation.engine import SimulationEngine
from src.simulation.generators import (
    ArrivalGenerator,
    EmpiricalArrival,
    ServiceGenerator,
    EmpiricalService,
)

__all__ = [
    "SimulationConfig",
    "SimulationResult",
    "SimulationEngine",
    "ArrivalGenerator",
    "EmpiricalArrival",
    "ServiceGenerator",
    "EmpiricalService",
]
