"""CLI package for the web server traffic simulation pipeline.

Provides subcommand definitions (``commands``) and argument parsing
(``cli``) as separate modules so that ``__init__`` stays empty.
"""

from .cli import main

__all__ = ["main"]
