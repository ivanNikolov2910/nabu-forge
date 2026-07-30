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
    name: str


@dataclass(frozen=True)
class IRArgumentValue:
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
