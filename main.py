from loguru import logger

from src.ingestion import LogIngestor
from src.analysis import TrafficCharacterizer


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

    char = TrafficCharacterizer()
    result = char.run()
    logger.success(
        f"Characterization complete: arrival={result.arrival.is_poisson}, "
        f"best service dist={result.service.best_distribution}"
    )


if __name__ == "__main__":
    main()
