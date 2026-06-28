"""Analysis components for traffic characterization.

Each class has a single responsibility: binning, arrival testing,
or service-time fitting.  All produce a verdict dataclass plus
an optional matplotlib figure.
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.stats._continuous_distns import rv_continuous
from loguru import logger

from src.analysis._types import ArrivalVerdict, ServiceFit, ServiceVerdict

_RNG = np.random.default_rng(42)


class RateBinner:
    """Bin timestamps into a fixed-interval arrival-count series λ(t).

    The series is the empirical arrival rate over time, used to
    determine realistic λ values for the load sweep.
    """

    def __init__(self, df: pd.DataFrame, bin_seconds: int = 60) -> None:
        """Initialize the binner with a DataFrame and bin width.

        Args:
            df: DataFrame with a ``timestamp`` column.
            bin_seconds: Width of each bin in seconds (default 60).
        """
        self.df = df
        self.bin_seconds = bin_seconds
        self.series: pd.Series | None = None

    def fit(self) -> pd.Series:
        """Resample timestamps and count arrivals per bin."""
        logger.info(f"Binning arrivals into {self.bin_seconds}s intervals ...")
        ts = self.df["timestamp"]
        self.series = ts.dt.floor(f"{self.bin_seconds}s").value_counts().sort_index()
        return self.series


class ArrivalTester:
    """Test inter-arrival times against the exponential distribution.

    Uses ``scipy.stats.goodness_of_fit`` (parametric bootstrap)
    rather than a naive KS test, so the p-value correctly accounts
    for estimating the rate parameter from the same data.
    """

    def __init__(self, df: pd.DataFrame, mc_samples: int = 999) -> None:
        """Initialize the arrival tester with request data.

        Args:
            df: DataFrame with a ``timestamp`` column.
            mc_samples: Number of Monte Carlo samples for the GoF
                test (default 999).
        """
        self.df = df
        self.mc_samples = mc_samples
        self.interarrivals: np.ndarray | None = None
        self.lambda_: float | None = None

    def test(self) -> ArrivalVerdict:
        """Compute inter-arrival times and run the GoF test."""
        times = self.df["timestamp"].sort_values()
        diffs = times.diff().dt.total_seconds().to_numpy()
        self.interarrivals = diffs[diffs > 0]
        n = len(self.interarrivals)
        logger.info(f"Testing {n} inter-arrival times ...")

        _, scale = sp_stats.expon.fit(self.interarrivals, floc=0)
        self.lambda_ = 1.0 / scale

        # Subsample for GoF: KS test with huge N has excessive power.
        # A random 10000-point subsample is standard practice.
        rng = np.random.default_rng(42)
        sample = rng.choice(self.interarrivals, size=10000, replace=False)

        res = sp_stats.goodness_of_fit(
            sp_stats.expon,
            sample,
            known_params={"loc": 0},
            statistic="ks",
            n_mc_samples=self.mc_samples,
            rng=_RNG,
        )

        logger.info(
            f"KS stat={res.statistic:.5f}, p={res.pvalue:.4f}, "
            f"λ={self.lambda_:.3f} req/s"
        )
        return ArrivalVerdict(
            is_poisson=res.pvalue > 0.05,
            lambda_=self.lambda_,
            ks_statistic=float(res.statistic),
            ks_pvalue=float(res.pvalue),
            n_observations=n,
        )


class ServiceFitter:
    """Fit heavy-tailed distributions to HTTP response sizes.

    Evaluates Pareto (Type I) and Lognormal, recording AIC, BIC,
    and KS statistic for each candidate.  The best distribution
    minimises AIC.
    """

    _CANDIDATES: list[tuple[str, rv_continuous, int]] = [
        ("pareto", sp_stats.pareto, 2),
        ("lognorm", sp_stats.lognorm, 2),
    ]

    def __init__(self, df: pd.DataFrame) -> None:
        """Initialize the service-time fitter with response data.

        Args:
            df: DataFrame with a ``bytes`` column.
        """
        self.df = df
        self.sizes: np.ndarray | None = None

    def fit(self) -> ServiceVerdict:
        """Fit all candidates and return the best by AIC."""
        sizes = self.df["bytes"].dropna().to_numpy()
        # Remove zeros (304 responses with no body)
        sizes = sizes[sizes > 0]
        self.sizes = sizes
        n = len(sizes)
        logger.info(f"Fitting distributions to {n} response sizes ...")

        self.fits: list[ServiceFit] = []
        for name, dist, k in self._CANDIDATES:
            params = cast(rv_continuous, dist).fit(sizes, floc=0)
            loglik = float(np.sum(dist.logpdf(sizes, *params)))
            aic = float(2 * k - 2 * loglik)
            bic = float(k * np.log(n) - 2 * loglik)

            ks_stat = float(
                sp_stats.kstest(
                    sizes, lambda x, d=dist, p=params: d.cdf(x, *p)
                ).statistic
            )
            self.fits.append(
                ServiceFit(
                    distribution=name,
                    params={k: float(v) for k, v in zip(_param_names(dist), params)},
                    aic=round(aic, 1),
                    bic=round(bic, 1),
                    ks_statistic=round(ks_stat, 5),
                )
            )
            logger.info(f"  {name}: AIC={aic:.0f}, KS={ks_stat:.4f}")

        best = min(self.fits, key=lambda f: f.aic)
        logger.info(f"Best: {best.distribution} (AIC={best.aic})")
        return ServiceVerdict(
            best_distribution=best.distribution,
            comparisons=self.fits,
        )


def _param_names(dist) -> list[str]:
    """Return parameter names for a scipy continuous distribution.

    Args:
        dist: A scipy continuous distribution instance.

    Returns:
        List of parameter name strings ordered as ``dist.fit()``
        returns them.
    """
    shapes = dist.shapes
    if shapes is None:
        return ["loc", "scale"]
    return [s.strip() for s in shapes.split(",")] + ["loc", "scale"]
