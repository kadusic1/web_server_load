"""Empirical (bootstrap) fallback for the simulation layer.

When the exponential or heavy-tailed assumptions fail (expected for
real web traffic), this module provides generators that resample
directly from the observed trace.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger


class EmpiricalSaver:
    """Extract empirical traces and persist as NumPy ``.npy`` arrays.

    The arrays are consumed by the simulation engine when the
    theoretical distribution path is not selected.
    """

    def __init__(self, df: pd.DataFrame) -> None:
        """Initialize the saver with the full parsed DataFrame.

        Args:
            df: DataFrame with ``timestamp`` and ``bytes`` columns.
        """
        self.df = df

    def save(
        self,
        dst: str = "data",
        prefix: str = "empirical",
    ) -> None:
        """Write inter-arrival times and response sizes to ``.npy``.

        Args:
            dst: Output directory (default ``"data"``).
            prefix: Filename prefix (default ``"empirical"``).
        """
        out = Path(dst)
        out.mkdir(parents=True, exist_ok=True)

        times = self.df["timestamp"].sort_values()
        diffs = times.diff().dt.total_seconds().to_numpy()
        diffs = diffs[1:]  # first is NaN
        interarrivals = diffs[diffs > 0]

        sizes = self.df["bytes"].dropna().to_numpy()
        sizes = sizes[sizes > 0]

        np.save(out / f"{prefix}_interarrivals.npy", interarrivals)
        np.save(out / f"{prefix}_service_sizes.npy", sizes)

        logger.info(
            f"Saved {len(interarrivals)} inter-arrival gaps, {len(sizes)} service sizes"
        )
