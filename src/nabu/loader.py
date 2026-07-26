from pathlib import Path

from nabu.config import Config
from nabu.diagnostics import Diagnostic, DiagnosticReporter


def verify_paths(config: Config, base: Path, reporter: DiagnosticReporter) -> bool:
    ok = True

    schema = base / config.schema
    if not schema.exists():
        reporter.add(Diagnostic(
            code="E010",
            severity="error",
            message=f"Schema file not found: {schema}",
            file=str(schema),
        ))
        ok = False

    ops = base / config.operations
    if not ops.exists():
        reporter.add(Diagnostic(
            code="E011",
            severity="error",
            message=f"Operations directory not found: {ops}",
            file=str(ops),
        ))
        ok = False

    return ok


def list_operation_files(config: Config, base: Path) -> list[Path]:
    ops = base / config.operations
    return sorted(ops.glob("**/*.graphql")) + sorted(ops.glob("**/*.graphqls"))
