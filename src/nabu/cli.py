import dataclasses
import json
from enum import Enum
from importlib.metadata import version as lib_version
from pathlib import Path
from typing import Annotated

import typer

from nabu.config import load_config
from nabu.diagnostics.reporter import DiagnosticReporter
from nabu.loader.files import list_operation_files, verify_paths
from nabu.model.symbol_table import SymbolTable, dependency_order
from nabu.parser.operations import parse_operations
from nabu.parser.schema import parse_schema
from nabu.parser.traverse import summarise

app = typer.Typer(no_args_is_help=True)


class _SymbolTableEncoder(json.JSONEncoder):
    def default(self, o: object) -> object:
        if isinstance(o, SymbolTable):
            return {
                "symbols": o.symbols,
                "operations": {op.name: op for op in o.all_operations()},
                "dependency_order": dependency_order(o),
            }
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            return dataclasses.asdict(o)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)


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


@app.command("debug-symbols")
def debug_symbols(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to nabu.toml."),
    ] = Path("nabu.toml"),
) -> None:
    reporter = DiagnosticReporter()
    config = load_config(config_path, reporter)
    reporter.exit_if_errors()

    base = config_path.parent
    schema_path = base / config.schema
    schema = parse_schema(schema_path, reporter)
    reporter.exit_if_errors()

    if schema is None:
        return

    op_files = list_operation_files(config, base)
    documents = parse_operations(op_files, schema, reporter)
    reporter.exit_if_errors()

    table = SymbolTable(schema, documents, reporter)
    reporter.exit_if_errors()

    out_path = Path("debug-symbols.json")
    out_path.write_text(json.dumps(table, indent=2, cls=_SymbolTableEncoder))
    typer.echo(f"Written to {out_path.resolve()}")


def main() -> None:
    app()
