import dataclasses
import json
from enum import Enum
from importlib.metadata import version as lib_version
from pathlib import Path
from typing import Annotated

import typer

from nabu.context import CompilerContext
from nabu.diagnostics.reporter import DiagnosticReporter
from nabu.model.symbol_table import SymbolTable, dependency_order
from nabu.parser.schema import parse_schema
from nabu.parser.traverse import summarise

app = typer.Typer(no_args_is_help=True)


# TODO: Remove this, it is only used for debugging.
class _DebugEncoder(json.JSONEncoder):
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
    ctx = CompilerContext(config_path)
    ctx.load()
    ctx.verify()
    typer.echo("OK")


@app.command()
def inspect(
    schema: Annotated[
        Path, typer.Option("--schema", "-s", help="Path to the GraphQL schema file.")
    ],
) -> None:
    reporter = DiagnosticReporter()
    parsed = reporter.collect(parse_schema(schema))

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


# TODO: Remove this, it is only used for debugging.
@app.command("debug-symbols")
def debug_symbols(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to nabu.toml."),
    ] = Path("nabu.toml"),
) -> None:
    ctx = CompilerContext(config_path)
    ctx.load()
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    table = ctx.build_symbols(schema, documents)

    out_path = Path("debug-symbols.json")
    out_path.write_text(json.dumps(table, indent=2, cls=_DebugEncoder))
    typer.echo(f"Written to {out_path.resolve()}")


# TODO: Remove this, it is only used for debugging.
@app.command("debug-ir")
def debug_ir(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to nabu.toml."),
    ] = Path("nabu.toml"),
) -> None:
    ctx = CompilerContext(config_path)
    ctx.load()
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    document = ctx.build_ir(schema, documents)

    out_path = Path("debug-ir.json")
    out_path.write_text(json.dumps(document, indent=2, cls=_DebugEncoder))
    typer.echo(f"Written to {out_path.resolve()}")


def main() -> None:
    app()
