"""Overload knee detection for load-sweep experiment results."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from kneed import KneeLocator
from loguru import logger

from src.experiment._config import ExperimentResult


def compute_overload_analysis(
    result: ExperimentResult,
    mu: float,
    dst: str = "data",
) -> None:
    """Run Kneedle-based overload detection and write analysis JSON.

    Args:
        result: Aggregated experiment results.
        mu: Service rate (req/s).
        dst: Output directory (default ``"data"``).
    """
    rows = result.rows
    rho = np.array([r.rho_actual for r in rows])
    p99 = np.array([r.p99_wait for r in rows])

    baseline_p95 = float(np.mean([r.p95_wait for r in rows[:3]]))
    baseline_p99 = float(np.mean([r.p99_wait for r in rows[:3]]))

    kl = KneeLocator(
        rho,
        p99,
        curve="convex",
        direction="increasing",
        S=1.0,
    )

    knee_rho = float(kl.knee) if kl.knee is not None else None
    knee_row = None
    if knee_rho is not None:
        for r in rows:
            if abs(r.rho_actual - knee_rho) < 1e-6:
                knee_row = r
                break

    method = (
        "Kneedle algorithm (Satopaa et al. 2011) applied to "
        "measured utilisation (rho_actual) vs p99 wait time, "
        f"with curve='convex', direction='increasing', S=1.0. "
        f"Low-load baseline computed from first 3 rho levels: "
        f"p95={baseline_p95:.4f}s, p99={baseline_p99:.4f}s."
    )

    levels = []
    for r in rows:
        levels.append(
            {
                "rho": r.rho,
                "rho_actual": r.rho_actual,
                "p50_wait": r.p50_wait,
                "p95_wait": r.p95_wait,
                "p99_wait": r.p99_wait,
                "p95_factor": (
                    round(r.p95_wait / baseline_p95, 1) if baseline_p95 > 0 else None
                ),
                "p99_factor": (
                    round(r.p99_wait / baseline_p99, 1) if baseline_p99 > 0 else None
                ),
                "mean_wait": r.mean_wait,
                "n_replications": r.n_replications,
            }
        )

    data = {
        "mu": round(mu, 4),
        "baseline_p95": round(baseline_p95, 4),
        "baseline_p99": round(baseline_p99, 4),
        "method": method,
        "knee": {
            "rho": knee_rho,
            "rho_actual": float(knee_row.rho_actual) if knee_row else None,
            "p50_wait": float(knee_row.p50_wait) if knee_row else None,
            "p95_wait": float(knee_row.p95_wait) if knee_row else None,
            "p99_wait": float(knee_row.p99_wait) if knee_row else None,
            "p95_factor": (
                round(knee_row.p95_wait / baseline_p95, 1)
                if knee_row and baseline_p95 > 0
                else None
            ),
            "p99_factor": (
                round(knee_row.p99_wait / baseline_p99, 1)
                if knee_row and baseline_p99 > 0
                else None
            ),
            "lambda": (round(knee_rho * mu, 1) if knee_rho is not None else None),
        },
        "levels": levels,
    }

    path = Path(dst) / "overload_analysis.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    knee_lambda = round(knee_rho * mu, 1) if knee_rho is not None else None
    logger.success(
        f"Wrote overload analysis to {path} "
        f"(knee rho={knee_rho}, lambda={knee_lambda})",
    )
