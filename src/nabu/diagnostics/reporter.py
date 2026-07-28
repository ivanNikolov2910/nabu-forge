import sys
from typing import TypeVar

from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result

T = TypeVar("T")


class DiagnosticReporter:
    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []

    def add(self, diagnostic: Diagnostic) -> None:
        self._diagnostics.append(diagnostic)
        print(str(diagnostic), file=sys.stderr)

    def collect(self, result: Result[T]) -> T | None:
        for diagnostic in result.diagnostics:
            self.add(diagnostic)
        self.exit_if_errors()
        return result.value

    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self._diagnostics)

    def exit_if_errors(self) -> None:
        if self.has_errors():
            sys.exit(1)
