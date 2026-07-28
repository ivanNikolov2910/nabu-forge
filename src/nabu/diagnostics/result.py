from dataclasses import dataclass, field
from typing import Generic, TypeVar

from nabu.diagnostics.diagnostic import Diagnostic

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    value: T | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return any(d.severity == "error" for d in self.diagnostics)
