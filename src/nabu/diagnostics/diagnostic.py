from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from graphql import GraphQLError

from nabu.diagnostics.codes import ErrorCode


@dataclass
class Diagnostic:
    code: ErrorCode
    severity: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    hint: str | None = None

    def __str__(self) -> str:
        location = ""
        if self.file:
            location = self.file
            if self.line is not None:
                location += f":{self.line}"
                if self.column is not None:
                    location += f":{self.column}"
            location += ": "
        hint = f"\n  hint: {self.hint}" if self.hint else ""
        return f"{location}[{self.code}] {self.severity}: {self.message}{hint}"

    @classmethod
    def from_graphql_error(
        cls, error: GraphQLError, code: ErrorCode, path: Path
    ) -> Diagnostic:
        loc = error.locations[0] if error.locations else None
        return cls(
            code=code,
            severity="error",
            message=error.message,
            file=str(path),
            line=loc.line if loc else None,
            column=loc.column if loc else None,
        )
