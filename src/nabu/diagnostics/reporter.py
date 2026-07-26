import sys
from dataclasses import dataclass

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


class DiagnosticReporter:
    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []

    def add(self, diagnostic: Diagnostic) -> None:
        self._diagnostics.append(diagnostic)
        print(str(diagnostic), file=sys.stderr)

    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self._diagnostics)

    def exit_if_errors(self) -> None:
        if self.has_errors():
            sys.exit(1)
