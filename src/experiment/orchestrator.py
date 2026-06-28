"""Load-sweep experiment orchestrator.

Runs the simulation engine across a range of target utilisations,
aggregating results across replications per load level.
"""

from __future__ import annotations

import itertools
import json
import time
from dataclasses import asdict

import numpy as np
from loguru import logger
from scipy import stats as sp_stats

from src.experiment._analysis import compute_overload_analysis
from src.experiment._config import (
    ExperimentConfig,
    ExperimentResult,
    LoadLevelRow,
)
from src.experiment._plot import plot_response_time_vs_load
from src.experiment._replication import run_replications
from src.simulation._types import SimulationResult


class ExperimentOrchestrator:
    """Coordinate load-sweep experiment with replications.

    Args:
        config: Experiment configuration. Uses defaults if
            ``None``.
    """

    def __init__(self, config: ExperimentConfig | None = None) -> None:
        self.config = config or ExperimentConfig()

    def run(self) -> ExperimentResult:
        """Run the load-sweep experiment.

        Returns:
            Aggregated results across all load levels.

        Raises:
            RuntimeError: If empirical trace files are missing.
        """
        cfg = self.config
        sim_cfg = cfg.simulation

        interarrivals = np.load(cfg.interarrivals_path)
        service_sizes = np.load(cfg.service_sizes_path)
        service_times = service_sizes / sim_cfg.bandwidth

        mu = 1.0 / float(np.mean(service_times))
        lambda_0 = 1.0 / float(np.mean(interarrivals))

        rho_points = np.concatenate(
            [
                np.linspace(0.1, 0.7, 4, endpoint=False),
                np.linspace(0.7, 1.3, 8, endpoint=False),
                np.linspace(1.3, 1.5, 3),
            ]
        )

        rows: list[LoadLevelRow] = []
        t_start = time.perf_counter()
        for i, rho in enumerate(rho_points):
            logger.info(
                f"Sweep rho={rho:.3f} ({i + 1}/{cfg.n_rho_points})",
            )

            lam_target = rho * sim_cfg.servers * mu
            scale = lambda_0 / lam_target
            scaled_interarrivals = interarrivals * scale

            results = run_replications(
                scaled_interarrivals,
                service_times,
                sim_cfg,
                cfg.n_replications,
            )

            row = self._aggregate(results, float(rho))
            rows.append(row)

            logger.success(
                f"rho={rho:.3f}: wait={row.mean_wait:.4f}s "
                f"[{row.ci_lower:.4f}, {row.ci_upper:.4f}], "
                f"p95={row.p95_wait:.4f}s",
            )

        result = ExperimentResult(rows=rows)
        self._write(result)
        plot_response_time_vs_load(result)
        compute_overload_analysis(result, mu)

        elapsed = time.perf_counter() - t_start
        logger.success(
            f"Sweep completed in {elapsed:.1f}s "
            f"({cfg.n_rho_points} levels x {cfg.n_replications} reps)",
        )
        return result

    @staticmethod
    def _aggregate(
        results: list[SimulationResult],
        rho: float,
    ) -> LoadLevelRow:
        """Aggregate replications into one output row.

        Args:
            results: Per-replication simulation results.
            rho: Target utilisation for this load level.

        Returns:
            Aggregated row with mean, CI, and percentiles.
        """
        n = len(results)
        means = [r.avg_wait for r in results]
        mean_wait = float(np.mean(means))

        if n >= 2:
            se = float(np.std(means, ddof=1)) / np.sqrt(n)
            ci_lower, ci_upper = sp_stats.t.interval(
                0.95,
                df=n - 1,
                loc=mean_wait,
                scale=se,
            )
        else:
            ci_lower = ci_upper = mean_wait

        all_waits = list(itertools.chain.from_iterable(r.waits for r in results))
        if all_waits:
            p50, p95, p99 = map(
                float,
                np.percentile(all_waits, [50, 95, 99]),
            )
        else:
            p50 = p95 = p99 = 0.0

        rho_actual = float(np.mean([r.server_utilization for r in results]))

        return LoadLevelRow(
            rho=rho,
            rho_actual=rho_actual,
            mean_wait=mean_wait,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p50_wait=p50,
            p95_wait=p95,
            p99_wait=p99,
            n_replications=n,
        )

    def _write(self, result: ExperimentResult) -> None:
        """Write results to JSON.

        Args:
            result: Experiment result to persist.
        """
        data = {
            "config": {
                "master_seed": self.config.master_seed,
                "n_replications": self.config.n_replications,
                "n_rho_points": self.config.n_rho_points,
                "rho_min": self.config.rho_min,
                "rho_max": self.config.rho_max,
            },
            "rows": [asdict(row) for row in result.rows],
        }
        path = self.config.output_path
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.success(
            f"Wrote {len(result.rows)} rows to {path}",
        )
