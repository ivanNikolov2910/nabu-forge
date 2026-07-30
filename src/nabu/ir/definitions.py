from dataclasses import dataclass

from nabu.ir.location import SourceLocation
from nabu.ir.types import TypeRef


@dataclass(frozen=True)
class IRArgument:
    name: str
    type_ref: TypeRef
    default_value: object | None = None


@dataclass
class IRField:
    name: str
    type_ref: TypeRef
    arguments: list[IRArgument]
    source_location: SourceLocation | None


@dataclass
class IRObjectType:
    name: str
    fields: list[IRField]
    interfaces: list[str]
    source_location: SourceLocation | None


@dataclass
class IRInputType:
    name: str
    fields: list[IRField]
    source_location: SourceLocation | None


@dataclass
class IREnumType:
    name: str
    values: list[str]
    source_location: SourceLocation | None


@dataclass
class IRScalarType:
    name: str
    builtin: bool
    source_location: SourceLocation | None


@dataclass
class IRInterfaceType:
    name: str
    fields: list[IRField]
    source_location: SourceLocation | None


@dataclass
class IRUnionType:
    name: str
    members: list[str]
    source_location: SourceLocation | None
