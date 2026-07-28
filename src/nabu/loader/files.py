from pathlib import Path

from nabu.config import Config
from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result


def verify_paths(config: Config, base: Path) -> Result[None]:
    diagnostics = []

    schema = base / config.schema
    if not schema.exists():
        diagnostics.append(
            Diagnostic(
                code=ErrorCode.SCHEMA_PATH_NOT_FOUND,
                severity="error",
                message=f"Schema file not found: {schema}",
                file=str(schema),
            )
        )

    ops = base / config.operations
    if not ops.exists():
        diagnostics.append(
            Diagnostic(
                code=ErrorCode.OPERATIONS_PATH_NOT_FOUND,
                severity="error",
                message=f"Operations directory not found: {ops}",
                file=str(ops),
            )
        )

    return Result(value=None, diagnostics=diagnostics)


def list_operation_files(config: Config, base: Path) -> list[Path]:
    ops = base / config.operations
    return sorted(ops.glob("**/*.graphql")) + sorted(ops.glob("**/*.graphqls"))
