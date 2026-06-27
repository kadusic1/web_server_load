"""Traffic characterization layer for NASA-HTTP logs.

Establishes the statistical properties of the real traffic before
any simulation code exists.  Produces the output contract for
Issue 3 (Simulation Engine).
"""

from src.traffic._types import (
    ArrivalVerdict,
    ServiceFit,
    ServiceVerdict,
    TrafficCharacterization,
)
from src.traffic.analyzers import RateBinner, ArrivalTester, ServiceFitter
from src.traffic.empirical import EmpiricalSaver
from src.traffic.characterizer import TrafficCharacterizer

__all__ = [
    "ArrivalVerdict",
    "ServiceFit",
    "ServiceVerdict",
    "TrafficCharacterization",
    "RateBinner",
    "ArrivalTester",
    "ServiceFitter",
    "EmpiricalSaver",
    "TrafficCharacterizer",
]
