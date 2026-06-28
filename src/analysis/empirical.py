"""Empirical (bootstrap) fallback for the simulation layer.

When the exponential or heavy-tailed assumptions fail (expected for
real web traffic), this module provides generators that resample
directly from the observed trace.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from loguru import logger


class EmpiricalSaver:
    """Extract empirical traces and persist as NumPy ``.npy`` arrays.

    The arrays are consumed by the simulation engine when the
    theoretical distribution path is not selected.
    """

    def __init__(
        self,
        interarrivals: np.ndarray,
        sizes: np.ndarray,
    ) -> None:
        """Initialize the saver with pre-computed empirical traces.

        Args:
            interarrivals: Inter-arrival times (seconds) derived from the
                parsed timestamp column.
            sizes: HTTP response sizes (bytes) derived from the parsed
                bytes column.
        """
        self.interarrivals = interarrivals
        self.sizes = sizes

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

        np.save(out / f"{prefix}_interarrivals.npy", self.interarrivals)
        np.save(out / f"{prefix}_service_sizes.npy", self.sizes)

        logger.info(
            f"Saved {len(self.interarrivals)} inter-arrival gaps, "
            f"{len(self.sizes)} service sizes"
        )
