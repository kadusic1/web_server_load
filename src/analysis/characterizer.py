"""Orchestrator that runs the full traffic characterization pipeline.

Loads the validated Parquet, runs all analyzers, persists the
output contract, and writes the human-readable report.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from loguru import logger

from src.analysis._types import TrafficCharacterization
from src.analysis.analyzers import RateBinner, ArrivalTester, ServiceFitter
from src.analysis._plot import plot_rate, plot_interarrivals, plot_service
from src.analysis.empirical import EmpiricalSaver

matplotlib.use("Agg")


class TrafficCharacterizer:
    """Orchestrate the full traffic characterization pipeline.

    Usage::

        char = TrafficCharacterizer()
        char.run()
    """

    def __init__(
        self,
        parquet_path: str = "data/parsed.parquet",
        bin_seconds: int = 60,
    ) -> None:
        """Initialize the pipeline with file paths and bin width.

        Args:
            parquet_path: Path to the parsed Parquet file
                (default ``"data/parsed.parquet"``).
            bin_seconds: Width of each rate bin in seconds
                (default 60).
        """
        self.parquet_path = parquet_path
        self.bin_seconds = bin_seconds
        self.df: pd.DataFrame | None = None
        self.result: TrafficCharacterization | None = None
        self._interarrivals: np.ndarray | None = None
        self._sizes: np.ndarray | None = None
        self._lambda: float | None = None
        self._rate_series: pd.Series | None = None

    def run(self) -> TrafficCharacterization:
        """Execute the pipeline: load, analyze, persist, report.

        Returns:
            TrafficCharacterization with arrival and service verdicts.
        """
        self._load()
        self._rate_bin()
        self._test_arrivals()
        self._fit_service()
        self._save_empirical()
        self._write_json()
        assert self.result is not None
        return self.result

    def _load(self) -> None:
        """Load the parsed Parquet file into ``self.df``."""
        logger.info(f"Loading {self.parquet_path} ...")
        self.df = pd.read_parquet(self.parquet_path)
        logger.info(f"Loaded {len(self.df)} rows")

    def _rate_bin(self) -> None:
        """Bin arrival timestamps and record rate statistics."""
        assert self.df is not None
        binner = RateBinner(self.df, self.bin_seconds)
        series = binner.fit()
        self._rate_min = float(series.min())
        self._rate_max = float(series.max())
        self._rate_mean = float(series.mean())
        self._rate_series = series
        plot_rate(series, self.bin_seconds)

    def _test_arrivals(self) -> None:
        """Test inter-arrival times against exponential distribution."""
        assert self.df is not None
        tester = ArrivalTester(self.df)
        self._arrival_verdict = tester.test()
        self._interarrivals = tester.interarrivals
        self._lambda = tester.lambda_
        assert self._interarrivals is not None
        assert self._lambda is not None
        plot_interarrivals(self._interarrivals, self._lambda)

    def _fit_service(self) -> None:
        """Fit heavy-tailed distributions to response sizes."""
        assert self.df is not None
        fitter = ServiceFitter(self.df)
        self._service_verdict = fitter.fit()
        self._sizes = fitter.sizes
        assert self._sizes is not None
        plot_service(self._sizes, fitter.fits)

    def _save_empirical(self) -> None:
        """Persist empirical traces as NumPy ``.npy`` arrays."""
        assert self.df is not None
        saver = EmpiricalSaver(self.df)
        saver.save()

    def _write_json(self) -> None:
        """Assemble and persist the characterization JSON."""
        self.result = TrafficCharacterization(
            arrival=self._arrival_verdict,
            service=self._service_verdict,
            bin_seconds=self.bin_seconds,
            rate_min=round(self._rate_min, 1),
            rate_max=round(self._rate_max, 1),
            rate_mean=round(self._rate_mean, 1),
        )
        path = Path("data/characterization.json")
        with path.open("w") as f:
            json.dump(self.result.to_dict(), f, indent=2)
        logger.success(f"Wrote {path}")
