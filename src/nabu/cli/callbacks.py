import logging
from typing import Annotated

import typer


def verbose_callback(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show debug output.")
    ] = False,
) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="  %(message)s")
