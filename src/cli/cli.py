"""Argument parser construction and dispatch.

Builds the :mod:`argparse` hierarchy and dispatches to the
appropriate :mod:`src.cli.commands` handler.  This module is the
composition root — no business logic lives here.
"""

from __future__ import annotations

import argparse

from src.cli import commands


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser with subcommands.

    Returns:
        An :class:`argparse.ArgumentParser` configured with four
        subcommands: ``ingest``, ``analyze``, ``simulate``, ``all``.
    """
    parser = argparse.ArgumentParser(
        description="Web server traffic simulation pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Parse raw logs into parquet")
    sub.add_parser("analyze", help="Analyze traffic patterns")
    sub.add_parser("simulate", help="Run single-shot simulation")
    sub.add_parser("sweep", help="Run load-sweep experiment with replications")
    sub.add_parser("all", help="Run full pipeline: ingest + analyze + simulate")

    return parser


def main() -> None:
    """Parse CLI arguments and dispatch to the matching command.

    The ``command`` field from the parsed namespace selects which
    handler in :mod:`src.cli.commands` is invoked.  No command
    accepts additional flags at present.
    """
    match build_parser().parse_args().command:
        case "ingest":
            commands.cmd_ingest()
        case "analyze":
            commands.cmd_analyze()
        case "simulate":
            commands.cmd_simulate()
        case "sweep":
            commands.cmd_sweep()
        case "all":
            commands.cmd_all()
