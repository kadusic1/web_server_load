"""Standalone plotting functions for traffic characterization.

Each function produces a single figure file on disk.  Extracted
from ``characterizer.py`` to keep the orchestrator focused on
orchestration.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from src.analysis._types import ServiceFit
from src.analysis.analyzers import _param_names


def plot_rate(
    series: pd.Series,
    bin_seconds: int,
    dst: str = "data",
) -> None:
    """Plot the arrival-rate time series.

    Args:
        series: Rate series indexed by timestamp.
        bin_seconds: Bin width used for the series.
        dst: Output directory (default ``"data"``).
    """
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(series.index.to_numpy(), series.to_numpy(), linewidth=0.4, alpha=0.7)
    ax.set(
        xlabel="Time",
        ylabel=f"Requests / {bin_seconds}s",
        title=f"Arrival Rate λ(t), {bin_seconds}s bins",
    )
    fig.tight_layout()
    fig.savefig(Path(dst) / "rate_series.png", dpi=150)
    plt.close(fig)


def plot_interarrivals(
    interarrivals: np.ndarray,
    lambda_: float,
    dst: str = "data",
) -> None:
    """Plot inter-arrival histogram and Q-Q plot vs exponential.

    Args:
        interarrivals: Observed inter-arrival times (seconds).
        lambda_: Fitted arrival rate (events/sec).
        dst: Output directory (default ``"data"``).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
    ax1.hist(interarrivals, bins=100, density=True, alpha=0.6, color="steelblue")
    x = np.linspace(0, np.percentile(interarrivals, 99.5), 300)
    ax1.plot(
        x,
        sp_stats.expon.pdf(x, loc=0, scale=1 / lambda_),
        "r-",
        linewidth=1.5,
        label=f"Expon(λ={lambda_:.2f})",
    )
    ax1.set(xlabel="Inter-arrival time (s)", ylabel="Density")
    ax1.legend()

    sp_stats.probplot(
        interarrivals,
        dist=sp_stats.expon(loc=0, scale=1 / lambda_),
        plot=ax2,
    )
    ax2.set_title("Q-Q Plot vs Exponential")

    fig.tight_layout()
    fig.savefig(Path(dst) / "interarrival_histogram.png", dpi=150)
    plt.close(fig)


def plot_service(
    sizes: np.ndarray,
    fits: list[ServiceFit],
    dst: str = "data",
) -> None:
    """Plot log-binned histogram with fitted distribution overlays.

    Args:
        sizes: Observed response sizes (bytes).
        fits: Fitted distribution results.
        dst: Output directory (default ``"data"``).
    """
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(
        np.log10(sizes),
        bins=80,
        density=True,
        alpha=0.6,
        color="steelblue",
        label="Empirical",
    )

    for fit in fits:
        dist = getattr(sp_stats, fit.distribution)
        params = _unpack_params(fit)
        x = np.logspace(np.log10(sizes.min()), np.log10(sizes.max()), 500)
        pdf = dist.pdf(x, *params)
        pdf_log = pdf * x * np.log(10)
        ax.plot(
            np.log10(x),
            pdf_log,
            linewidth=1.5,
            label=fit.distribution,
        )

    ax.set(
        xlabel="log₁₀(Response size / bytes)",
        ylabel="Density",
        title="Service-Time Distribution Fit",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(Path(dst) / "service_time_fit.png", dpi=150)
    plt.close(fig)


def _unpack_params(fit: ServiceFit) -> tuple:
    """Rebuild the scipy parameter tuple from a ServiceFit record.

    Args:
        fit: A ServiceFit instance with a ``params`` dict.

    Returns:
        Parameter tuple ordered for the scipy distribution's
        ``pdf`` / ``cdf`` methods.
    """
    dist = getattr(sp_stats, fit.distribution)
    names = _param_names(dist)
    return tuple(fit.params[n] for n in names)
