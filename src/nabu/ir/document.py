from dataclasses import dataclass, field

from nabu.ir.definitions import (
    IREnumType,
    IRField,
    IRInputType,
    IRInterfaceType,
    IRObjectType,
    IRScalarType,
    IRUnionType,
)
from nabu.ir.operations import IRFragment, IROperation


@dataclass
class IRDocument:
    objects: list[IRObjectType]
    inputs: list[IRInputType]
    enums: list[IREnumType]
    scalars: list[IRScalarType]
    interfaces: list[IRInterfaceType]
    unions: list[IRUnionType]
    operations: list[IROperation]
    fragments: list[IRFragment]
    query_fields: list[IRField] = field(default_factory=list)
    mutation_fields: list[IRField] = field(default_factory=list)
