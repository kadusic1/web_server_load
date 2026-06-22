"""Log ingestion for NCSA Common Log Format.

Only component allowed to touch raw log text. Produces one validated
Parquet file, one row per parsed request, plus a JSON quality summary.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Self

import pandas as pd
import pyarrow as pa
from loguru import logger


@dataclass(frozen=True)
class LogRecord:
    """One parsed HTTP request from the NASA-HTTP trace.

    Attributes:
        host: Remote host name or IP address.
        timestamp: Request timestamp with parsed UTC offset.
        method: HTTP method (GET, POST, HEAD, etc.).
        path: Requested URI path.
        status: HTTP response status code.
        bytes: Response size in bytes. NaN when the server logged '-'
            for a zero-length or missing response.
    """

    host: str
    timestamp: str
    method: str
    path: str
    status: int
    bytes: float | None


@dataclass
class Summary:
    """Quality summary for an ingestion run.

    Attributes:
        total_lines: Total number of lines in the raw log file.
        parsed_count: Number of lines successfully parsed.
        malformed_count: Number of lines that failed to parse.
        malformed_rate: Ratio of malformed to total lines (0.0–1.0).
    """

    total_lines: int
    parsed_count: int
    malformed_count: int
    malformed_rate: float


# Stable schema for the validated log table (Issue 2+ consumers
# rely on these column names and types without inspecting the parser).
SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("host", pa.string(), nullable=False),
        pa.field("timestamp", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("method", pa.string(), nullable=False),
        pa.field("path", pa.string(), nullable=False),
        pa.field("status", pa.int64(), nullable=False),
        pa.field("bytes", pa.float64()),
    ]
)

# NCSA Common Log Format with named capture groups.
# Groups: host, timestamp, method, path, status, bytes.
_LOG_PATTERN: re.Pattern[str] = re.compile(
    r"^(?P<host>\S+)"
    r" - - "
    r"\[(?P<timestamp>[^\]]+)\]"
    r' "(?P<method>\S+)'
    r" (?P<path>\S+)"
    r"(?: \S+)?"
    r'" '
    r"(?P<status>\d{3})"
    r" (?P<bytes>\S+)$",
)


class LogIngestor:
    """Parse, validate, and persist NCSA Common Log Format files.

    Method-chaining pipeline::

        ingestor = LogIngestor().run()
        # or step by step:
        ingestor = LogIngestor().read().parse().validate().write()

    State lives on ``self`` between steps. Run once per dataset;
    downstream components read the Parquet file, never raw text.

    The log file is downloaded from Kaggle via ``kagglehub`` and
    cached in ``~/.cache/kagglehub/`` (no local file needed).
    """

    KAGGLE_DATASET = "adchatakora/nasa-http-access-logs"

    def __init__(self) -> None:
        self._path: str = self._resolve_log()
        self._lines: pd.Series | None = None
        self._raw: pd.DataFrame | None = None
        self.valid: pd.DataFrame | None = None
        self.summary: Summary | None = None

    @staticmethod
    def _resolve_log() -> str:
        """Locate the log file, downloading from Kaggle if needed.

        Returns:
            Absolute path to the NCSA Common Log file on disk.
        """
        import kagglehub

        cached = kagglehub.dataset_download(LogIngestor.KAGGLE_DATASET)
        return str(next(Path(cached).glob("*.log")))

    def read(self) -> Self:
        """Load raw log lines from the Kaggle-cached log file.

        Returns:
            ``self`` so the next pipeline method can be chained.
        """
        logger.info(f"Reading {self._path} ...")
        with open(self._path, encoding="utf-8", errors="replace") as f:
            self._lines = pd.Series(f.readlines(), dtype="str")
        return self

    def parse(self) -> Self:
        """Extract structured fields via vectorized ``str.extract``.

        Applies :attr:`_LOG_PATTERN` across every line.  Named capture
        groups become DataFrame columns.  Non-matching rows produce
        ``NaN`` in all columns and are flagged as malformed later.

        Returns:
            ``self`` for method chaining.
        """
        assert self._lines is not None, "call read() first"
        logger.info(f"Parsing {len(self._lines)} lines ...")
        self._raw = self._lines.str.extract(_LOG_PATTERN)
        return self

    def validate(self) -> Self:
        """Validate parsed rows, coerce types, and produce a summary.

        Malformed lines (those with any ``NaN`` from the regex) are
        counted and excluded.  The ``bytes`` column normalises ``"-"`
        to ``NaN``, ``status`` becomes ``int64``, and ``timestamp`` is
        parsed with its UTC offset preserved via ``pd.to_datetime``.

        Returns:
            ``self`` for method chaining.
        """
        assert self._raw is not None, "call parse() first"
        logger.info("Validating ...")
        total = len(self._raw)
        malformed = self._raw.isna().any(axis=1)
        malformed_count = malformed.sum()
        parsed_count = total - malformed_count
        valid = self._raw[~malformed].copy()
        valid["status"] = valid["status"].astype("int64")
        valid["bytes"] = pd.to_numeric(valid["bytes"], errors="coerce")
        valid["timestamp"] = pd.to_datetime(
            valid["timestamp"],
            format="%d/%b/%Y:%H:%M:%S %z",
            exact=True,
        )
        self.valid = valid
        rate = round(malformed_count / total, 6) if total > 0 else 0.0
        self.summary = Summary(
            total_lines=total,
            parsed_count=int(parsed_count),
            malformed_count=int(malformed_count),
            malformed_rate=rate,
        )
        return self

    def write(self, stem: str = "parsed") -> Self:
        """Persist the validated table as Parquet and JSON sidecar.

        Args:
            stem: Base name for output files (default ``"parsed"``).
                Produces ``data/<stem>.parquet`` and
                ``data/<stem>_summary.json``.

        Returns:
            ``self`` for method chaining.
        """
        assert self.valid is not None, "call validate() first"
        assert self.summary is not None
        logger.info(f"Writing output (stem='{stem}') ...")
        out = Path("data")
        out.mkdir(parents=True, exist_ok=True)
        self.valid.to_parquet(out / f"{stem}.parquet", index=False)
        with (out / f"{stem}_summary.json").open("w") as f:
            json.dump(asdict(self.summary), f, indent=2)
        return self

    def run(self, stem: str = "parsed") -> Self:
        """Convenience: read, parse, validate, and write in one call.

        Equivalent to ``self.read().parse().validate().write(stem)``.

        Args:
            stem: Passed through to :meth:`write`.

        Returns:
            ``self`` after the full pipeline has run.
        """
        return self.read().parse().validate().write(stem)
