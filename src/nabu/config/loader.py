import tomllib
from dataclasses import dataclass
from pathlib import Path

from nabu.diagnostics import Diagnostic, DiagnosticReporter, ErrorCode

_REQUIRED_FIELDS = ("schema", "operations", "output")


@dataclass
class Config:
    schema: str
    operations: str
    output: str


def load_config(path: Path, reporter: DiagnosticReporter) -> Config | None:
    if not path.exists():
        reporter.add(
            Diagnostic(
                code=ErrorCode.CONFIG_NOT_FOUND,
                severity="error",
                message=f"Config file not found: {path}",
            )
        )
        return None

    with path.open("rb") as f:
        data = tomllib.load(f)

    missing = [k for k in _REQUIRED_FIELDS if k not in data]
    if missing:
        reporter.add(
            Diagnostic(
                code=ErrorCode.CONFIG_MISSING_FIELDS,
                severity="error",
                message=f"Missing required fields in {path}: {', '.join(missing)}",
                file=str(path),
            )
        )
        return None

    return Config(
        schema=data["schema"],
        operations=data["operations"],
        output=data["output"],
    )
