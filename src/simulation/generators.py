"""Arrival and service time generators for the simulation engine.

Provides empirical (bootstrap resampling) generators for inter-arrival
and service times.  The engine consumes the abstract interface so
generator implementations are swappable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class _GeneratorBase(ABC):
    """Common base for arrival and service generators.

    Attributes:
        rng: NumPy Generator for random draws. The engine may replace
            this to ensure independent RNG streams.
    """

    rng: np.random.Generator

    @property
    @abstractmethod
    def rate(self) -> float:
        """Rate in requests per second."""


class ArrivalGenerator(_GeneratorBase):
    """Abstract inter-arrival time generator.

    Implementations produce the next inter-arrival time (seconds)
    on each call to :meth:`next_interarrival`.
    """

    @abstractmethod
    def next_interarrival(self) -> float:
        """Return the next inter-arrival time in seconds."""


class EmpiricalArrival(ArrivalGenerator):
    """Resample inter-arrival times from an empirical trace.

    Args:
        interarrivals: Array of observed inter-arrival times (seconds).
    """

    def __init__(self, interarrivals: np.ndarray) -> None:
        self._data: np.ndarray = interarrivals
        self.rng = np.random.default_rng()

    @property
    def rate(self) -> float:
        """Compute rate as 1 / mean of the empirical trace.

        Returns:
            Estimated rate in requests per second, or 0.0 if empty.
        """
        if len(self._data) == 0:
            return 0.0
        return float(1.0 / np.mean(self._data))

    def next_interarrival(self) -> float:
        return float(self.rng.choice(self._data))


class ServiceGenerator(_GeneratorBase):
    """Abstract service-time generator.

    Implementations produce the next service time (seconds) on each
    call to :meth:`next_service_time`.
    """

    @abstractmethod
    def next_service_time(self) -> float:
        """Return the next service time in seconds."""


class EmpiricalService(ServiceGenerator):
    """Resample service times from an empirical trace.

    The caller is responsible for converting raw byte sizes to seconds
    using the configured bandwidth *before* passing the array.

    Args:
        service_times: Array of observed service times (seconds).
    """

    def __init__(self, service_times: np.ndarray) -> None:
        self._data: np.ndarray = service_times
        self.rng = np.random.default_rng()

    @property
    def rate(self) -> float:
        """Compute rate as 1 / mean of the empirical trace.

        Returns:
            Estimated rate in requests per second, or 0.0 if empty.
        """
        if len(self._data) == 0:
            return 0.0
        return float(1.0 / np.mean(self._data))

    def next_service_time(self) -> float:
        return float(self.rng.choice(self._data))
