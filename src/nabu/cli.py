from importlib.metadata import version as lib_version
from pathlib import Path
from typing import Annotated

import typer

from nabu.config import load_config
from nabu.diagnostics import DiagnosticReporter
from nabu.loader import verify_paths
from nabu.parser.schema import parse_schema
from nabu.parser.traverse import summarise

app = typer.Typer(no_args_is_help=True)


@app.command()
def version() -> None:
    typer.echo(lib_version("nabu-forge"))


@app.command()
def validate(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config", "-c", help="Path to the config file, defaults to ./nabu.toml."
        ),
    ] = Path("nabu.toml"),
) -> None:
    reporter = DiagnosticReporter()
    config = load_config(config_path, reporter)
    reporter.exit_if_errors()

    verify_paths(config, config_path.parent, reporter)
    reporter.exit_if_errors()

    typer.echo("OK")


@app.command()
def inspect(
    schema: Annotated[
        Path, typer.Option("--schema", "-s", help="Path to the GraphQL schema file.")
    ],
) -> None:
    reporter = DiagnosticReporter()
    parsed = parse_schema(schema, reporter)
    reporter.exit_if_errors()

    if parsed is None:
        return

    summary = summarise(parsed)

    typer.echo(f"Schema: {schema}\n")
    typer.echo(f"  Object types : {len(summary.object_types)}")
    typer.echo(f"  Input types  : {len(summary.input_types)}")
    typer.echo(f"  Enums        : {len(summary.enums)}")
    typer.echo(f"  Scalars      : {len(summary.scalars)}")
    typer.echo(f"  Interfaces   : {len(summary.interfaces)}")
    typer.echo(f"  Unions       : {len(summary.unions)}")
    typer.echo(f"  Queries      : {len(summary.queries)}")
    typer.echo(f"  Mutations    : {len(summary.mutations)}")


def main() -> None:
    app()
