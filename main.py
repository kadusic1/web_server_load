"""CLI entry point

Usage::

    python main.py
"""

from loguru import logger

from src.ingestion.ingestor import LogIngestor


def main() -> None:
    ingestor = LogIngestor().run()

    if ingestor.summary is None:
        raise RuntimeError("ingestion pipeline did not produce a summary")
    s = ingestor.summary
    logger.success(
        f"Done: {s.parsed_count} parsed, "
        f"{s.malformed_count} malformed "
        f"(rate={s.malformed_rate}).",
    )


if __name__ == "__main__":
    main()
