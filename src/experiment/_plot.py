"""Standalone plotting function for the load-sweep experiment.

Produces the response-time-vs-utilisation plot with percentile
lines and confidence-interval ribbon.  Extracted so the
orchestrator stays focused on orchestration.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.experiment._config import ExperimentResult


def plot_response_time_vs_load(
    result: ExperimentResult,
    dst: str = "data",
) -> None:
    """Plot response-time percentiles vs measured utilisation.

    Args:
        result: Aggregated experiment results.
        dst: Output directory (default ``"data"``).
    """
    rows = result.rows
    rho = np.array([r.rho_actual for r in rows])
    p50 = np.array([r.p50_wait for r in rows])
    p95 = np.array([r.p95_wait for r in rows])
    p99 = np.array([r.p99_wait for r in rows])
    lo = np.array([r.ci_lower for r in rows])
    hi = np.array([r.ci_upper for r in rows])

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)

    ax.fill_between(
        rho,
        lo,
        hi,
        alpha=0.2,
        color="#0173B2",
        label="95% CI",
    )
    ax.plot(rho, p50, color="#0173B2", linewidth=1.5, label="p50")
    ax.plot(rho, p95, color="#DE8F05", linewidth=1.5, label="p95")
    ax.plot(rho, p99, color="#CC78BC", linewidth=1.5, label="p99")

    ax.axvline(
        x=1.0,
        color="red",
        linestyle="--",
        linewidth=1.0,
        alpha=0.7,
        label=r"$\rho = 1.0$",
    )

    ax.set_yscale("log")
    ax.set_xlabel(r"Measured utilisation $\rho$")
    ax.set_ylabel("Queue wait time (s)")
    ax.set_title("Response Time vs Load")
    ax.legend(loc="upper left")

    fig.savefig(Path(dst) / "response_time_vs_load.svg")
    plt.close(fig)
