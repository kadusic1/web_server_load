"""Command handlers for the simulation CLI.

Each function in this module corresponds to one ``main.py`` subcommand.
Functions are deliberately zero-argument — all configuration is read
from :class:`SimulationConfig` internally.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger

from src.ingestion import LogIngestor
from src.simulation import (
    EmpiricalArrival,
    EmpiricalService,
    SimulationConfig,
    SimulationEngine,
)
from src.analysis import TrafficCharacterizer
from src.experiment import ExperimentOrchestrator


def _require_empirical_traces() -> None:
    """Check that empirical trace files from analysis exist."""
    cfg = SimulationConfig()
    if (
        not Path(cfg.interarrivals_path).exists()
        or not Path(cfg.service_sizes_path).exists()
    ):
        raise RuntimeError(
            "empirical trace files not found in data/ "
            "- run `python main.py analyze` first"
        )


def cmd_ingest() -> None:
    """Parse raw NASA-HTTP logs into a cleaned Parquet file.

    Runs the full ingestion pipeline and logs a summary of parsed
    vs. malformed records.

    Raises:
        RuntimeError: If the ingestion pipeline produces no summary.
    """
    logger.info("Starting ingestion phase")
    ingestor = LogIngestor().run()
    if ingestor.summary is None:
        raise RuntimeError("ingestion pipeline did not produce a summary")
    s = ingestor.summary
    logger.success(
        f"Done: {s.parsed_count} parsed, "
        f"{s.malformed_count} malformed "
        f"(rate={s.malformed_rate}).",
    )


def cmd_analyze() -> None:
    """Analyze the parsed traffic trace.

    Fits a Poisson process to arrivals and fits candidate distributions
    to service times, then logs the best-fit results.

    Raises:
        RuntimeError: If ``data/parsed.parquet`` does not exist
            (ingestion has not been run yet).
    """
    logger.info("Starting analysis phase")
    if not Path("data/parsed.parquet").exists():
        raise RuntimeError(
            "parsed data not found at data/parsed.parquet "
            "- run `python main.py ingest` first"
        )
    char = TrafficCharacterizer()
    result = char.run()
    logger.success(
        f"Analysis complete: arrival={result.arrival.is_poisson}, "
        f"best service dist={result.service.best_distribution}"
    )


def cmd_simulate() -> None:
    """Run a single-shot discrete-event simulation.

    Loads empirical inter-arrival times and service sizes from
    :class:`SimulationConfig` paths, converts byte sizes to seconds
    using the configured bandwidth, then runs the SimPy engine and
    logs key metrics (utilisation, queue length, wait time).

    Raises:
        RuntimeError: If the empirical trace files are missing
            (analysis has not been run yet).
    """
    logger.info("Starting simulation phase")
    _require_empirical_traces()
    cfg = SimulationConfig()
    interarrivals = np.load(cfg.interarrivals_path)
    service_sizes = np.load(cfg.service_sizes_path)
    service_times = service_sizes / cfg.bandwidth

    arrival = EmpiricalArrival(interarrivals)
    service = EmpiricalService(service_times)
    engine = SimulationEngine(arrival, service, cfg)
    result = engine.run()
    logger.success(
        f"Simulation done: λ={result.lambda_:.3f}, μ={result.mu:.3f}, "
        f"wait={result.avg_wait:.4f}s, queue={result.avg_queue_length:.3f}, "
        f"util={result.server_utilization:.3f}, "
        f"requests={result.total_requests}"
    )


def cmd_sweep() -> None:
    """Run the load-sweep experiment with replications.

    Raises:
        RuntimeError: If empirical trace files are missing
            (analysis has not been run yet).
    """
    logger.info("Starting sweep phase")
    _require_empirical_traces()

    orch = ExperimentOrchestrator()
    orch.run()


def cmd_all() -> None:
    """Run the full pipeline: ingest, analyse, then simulate."""
    cmd_ingest()
    cmd_analyze()
    cmd_simulate()
