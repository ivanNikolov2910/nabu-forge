import dataclasses
import json
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from nabu.context import CompilerContext
from nabu.model.symbol_table import SymbolTable, dependency_order

debug = typer.Typer(help="Internal debug commands - not for production use.")


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


_CONFIG = typer.Option("--config", "-c", help="Path to nabu.toml.")


@debug.command("ir")
def debug_ir(
    config_path: Annotated[Path, _CONFIG] = Path("nabu.toml"),
) -> None:
    ctx = CompilerContext(config_path)
    ctx.load()
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    document = ctx.build_ir(schema, documents)
    out = Path("debug-ir.json")
    out.write_text(json.dumps(document, indent=2, cls=_DebugEncoder))
    typer.echo(f"Written to {out.resolve()}")
