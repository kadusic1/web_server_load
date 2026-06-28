"""Shared dataclasses for the traffic characterization layer.

Separated from ``__init__.py`` to avoid circular imports between
``__init__.py`` and the submodules.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class ArrivalVerdict:
    """Result of testing inter-arrival times against exponential.

    Attributes:
        is_poisson: True if KS test p-value > 0.05.
        lambda_: Estimated arrival rate (events/sec), or None.
        ks_statistic: Kolmogorov-Smirnov D statistic.
        ks_pvalue: Parametric bootstrap p-value.
        n_observations: Number of inter-arrival samples tested.
    """

    is_poisson: bool
    lambda_: float | None
    ks_statistic: float
    ks_pvalue: float
    n_observations: int


@dataclass
class ServiceFit:
    """Fit result for one candidate distribution.

    Attributes:
        distribution: Name of the distribution (e.g. 'pareto').
        params: Fitted parameters dict.
        aic: Akaike Information Criterion (lower = better).
        bic: Bayesian Information Criterion.
        ks_statistic: KS D statistic (absolute fit measure).
    """

    distribution: str
    params: dict
    aic: float
    bic: float
    ks_statistic: float


@dataclass
class ServiceVerdict:
    """Result of fitting heavy-tailed distributions to response sizes.

    Attributes:
        best_distribution: Name of the best-fitting distribution.
        comparisons: List of ServiceFit for all candidates.
    """

    best_distribution: str
    comparisons: list[ServiceFit]


@dataclass
class TrafficCharacterization:
    """Full output contract between Issue 2 and Issue 3.

    Attributes:
        arrival: Verdict on the arrival process.
        service: Verdict on the service-time distribution.
        bin_seconds: Bin width used for rate series.
        rate_min: Minimum arrival rate (req/bin).
        rate_max: Maximum arrival rate.
        rate_mean: Mean arrival rate.
    """

    arrival: ArrivalVerdict
    service: ServiceVerdict
    bin_seconds: int
    rate_min: float
    rate_max: float
    rate_mean: float

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return _convert(asdict(self))


def _convert(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert(v) for v in obj]
    if hasattr(obj, "dtype"):
        return obj.item()
    return obj
