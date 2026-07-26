from dataclasses import dataclass
from typing import TypeAlias

from graphql import OperationType


@dataclass
class FieldSymbol:
    name: str
    type_name: str
    non_null: bool
    is_list: bool


@dataclass
class VariableSymbol:
    name: str
    type_name: str
    non_null: bool


@dataclass
class ObjectTypeSymbol:
    name: str
    fields: list[FieldSymbol]
    interfaces: list[str]


@dataclass
class EnumTypeSymbol:
    name: str
    values: list[str]


@dataclass
class ScalarTypeSymbol:
    name: str
    builtin: bool


@dataclass
class InputTypeSymbol:
    name: str
    fields: list[FieldSymbol]


@dataclass
class InterfaceTypeSymbol:
    name: str
    fields: list[FieldSymbol]


@dataclass
class UnionTypeSymbol:
    name: str
    members: list[str]


@dataclass
class OperationSymbol:
    name: str
    operation_type: OperationType
    variables: list[VariableSymbol]
    selection: list[str]


Symbol: TypeAlias = (
    ObjectTypeSymbol
    | EnumTypeSymbol
    | ScalarTypeSymbol
    | InputTypeSymbol
    | InterfaceTypeSymbol
    | UnionTypeSymbol
)
