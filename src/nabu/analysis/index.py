from dataclasses import dataclass, field
from typing import TypeAlias

from nabu.graphql.schema_utils import BUILTIN_SCALARS
from nabu.ir.definitions import (
    IREnumType,
    IRField,
    IRInputType,
    IRInterfaceType,
    IRObjectType,
    IRScalarType,
    IRUnionType,
)
from nabu.ir.document import IRDocument
from nabu.ir.operations import IRFragment

IRTypeSymbol: TypeAlias = (
    IRObjectType
    | IRInputType
    | IREnumType
    | IRScalarType
    | IRInterfaceType
    | IRUnionType
)


@dataclass
class IRIndex:
    document: IRDocument
    types: dict[str, IRTypeSymbol] = field(default_factory=dict)
    fragments: dict[str, IRFragment] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for t in (
            self.document.objects
            + self.document.inputs
            + self.document.enums
            + self.document.scalars
            + self.document.interfaces
            + self.document.unions
        ):
            self.types[t.name] = t
        for f in self.document.fragments:
            self.fragments[f.name] = f
        for name, fields in (
            ("Query", self.document.query_fields),
            ("Mutation", self.document.mutation_fields),
        ):
            if fields:
                self.types[name] = IRObjectType(
                    name=name, fields=fields, interfaces=[], source_location=None
                )

    def is_defined(self, name: str) -> bool:
        return name in self.types or name in BUILTIN_SCALARS

    def field_of(self, type_name: str, field_name: str) -> IRField | None:
        t = self.types.get(type_name)
        if t is None or not hasattr(t, "fields"):
            return None
        return next((f for f in t.fields if f.name == field_name), None)
