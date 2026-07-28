from dataclasses import dataclass

from nabu.ir.definitions import (
    IREnumType,
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
