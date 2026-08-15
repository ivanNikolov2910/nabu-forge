from importlib.metadata import version as lib_version
from pathlib import Path
from typing import Annotated

import typer

from nabu.context import CompilerContext
from nabu.diagnostics.reporter import DiagnosticReporter
from nabu.parser.schema import parse_schema
from nabu.parser.traverse import summarise


def version() -> None:
    typer.echo(lib_version("nabu-forge"))


def validate(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config", "-c", help="Path to nabu.toml, defaults to ./nabu.toml."
        ),
    ] = Path("nabu.toml"),
) -> None:
    ctx = CompilerContext(config_path)
    ctx.load()
    ctx.verify()
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    ir = ctx.build_ir(schema, documents)
    ctx.analyse(ir)
    typer.echo("OK")


def generate(
    config_path: Annotated[
        Path,
        typer.Option(
            "--config", "-c", help="Path to nabu.toml, defaults to ./nabu.toml."
        ),
    ] = Path("nabu.toml"),
) -> None:
    ctx = CompilerContext(config_path)
    ctx.load()
    ctx.verify()
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    ir = ctx.build_ir(schema, documents)
    ctx.analyse(ir)
    stats, elapsed = ctx.generate(ir)
    typer.echo(
        f"OK  files={stats.total}  written={stats.written}"
        f"  skipped={stats.skipped}  time={elapsed:.2f}s"
    )


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
