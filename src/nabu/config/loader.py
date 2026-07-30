import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result

REQUIRED_FIELDS = ("schema", "operations", "output")


@dataclass
class Config:
    schema: str
    operations: str
    output: str
    scalars: dict[str, str] = field(default_factory=dict)


def load_config(path: Path) -> Result[Config]:
    if not path.exists():
        return Result(
            diagnostics=[
                Diagnostic(
                    code=ErrorCode.CONFIG_NOT_FOUND,
                    severity="error",
                    message=f"Config file not found: {path}",
                )
            ]
        )

    with path.open("rb") as f:
        data = tomllib.load(f)

    missing = [key for key in REQUIRED_FIELDS if key not in data]
    if missing:
        return Result(
            diagnostics=[
                Diagnostic(
                    code=ErrorCode.CONFIG_MISSING_FIELDS,
                    severity="error",
                    message=f"Missing required fields in {path}: {', '.join(missing)}",
                    file=str(path),
                )
            ]
        )

    return Result(
        value=Config(
            schema=data["schema"],
            operations=data["operations"],
            output=data["output"],
            scalars=data.get("scalars", {}),
        )
    )
