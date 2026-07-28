from __future__ import annotations

from dataclasses import dataclass

from graphql import OperationType

from nabu.ir.location import SourceLocation
from nabu.ir.types import TypeRef


@dataclass
class IRVariable:
    name: str
    type_ref: TypeRef
    default_value: object | None


@dataclass(frozen=True)
class IRVariableRef:
    """A reference to an operation variable used as an argument value,
    e.g. the `$id` in `student(id: $id)`."""

    name: str


@dataclass(frozen=True)
class IRArgumentValue:
    """An argument passed at an operation call site, e.g. `student(id: "123")`.
    Distinct from IRArgument, which declares an argument's type in the schema.
    `value` is a literal Python value, or an IRVariableRef for `$var` references."""

    name: str
    value: object


@dataclass
class IRFieldSelection:
    name: str
    alias: str | None
    arguments: list[IRArgumentValue]
    selections: list[IRSelection]
    source_location: SourceLocation | None


@dataclass
class IRInlineFragment:
    on_type: str
    selections: list[IRSelection]


@dataclass
class IRFragmentSpread:
    name: str


IRSelection = IRFieldSelection | IRInlineFragment | IRFragmentSpread


@dataclass
class IROperation:
    name: str
    operation_type: OperationType
    variables: list[IRVariable]
    selections: list[IRSelection]
    source_location: SourceLocation | None


@dataclass
class IRFragment:
    name: str
    on_type: str
    selections: list[IRSelection]
