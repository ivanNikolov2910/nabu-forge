import importlib
from importlib.metadata import version
from pathlib import Path

import typer

from nabu.config import load_config
from nabu.diagnostics import DiagnosticReporter
from nabu.loader import verify_paths

app = typer.Typer(no_args_is_help=True)


@app.command()
def version() -> None:
    typer.echo(importlib.metadata.version("nabu-forge"))


@app.command()
def validate(
    config_path: Path = typer.Option(Path("nabu.toml"), "--config", "-c"),
) -> None:

    reporter = DiagnosticReporter()
    config = load_config(config_path, reporter)
    reporter.exit_if_errors()

    verify_paths(config, config_path.parent, reporter)
    reporter.exit_if_errors()

    typer.echo("OK")


def main() -> None:
    app()
