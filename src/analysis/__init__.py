"""Traffic characterization layer for NASA-HTTP logs.

Establishes the statistical properties of the real traffic before
any simulation code exists.  Produces the output contract for
Issue 3 (Simulation Engine).
"""

from src.analysis._types import (
    ArrivalVerdict,
    ServiceFit,
    ServiceVerdict,
    TrafficCharacterization,
)
from src.analysis.analyzers import RateBinner, ArrivalTester, ServiceFitter
from src.analysis.empirical import EmpiricalSaver
from src.analysis.characterizer import TrafficCharacterizer

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
