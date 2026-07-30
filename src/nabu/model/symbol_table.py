from __future__ import annotations

from graphql import (
    DocumentNode,
    FieldNode,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLUnionType,
    OperationDefinitionNode,
)

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result
from nabu.graphql.schema_utils import BUILTIN_SCALARS, is_builtin, root_type_names
from nabu.ir.types import (
    ListTypeRef,
    NamedTypeRef,
    NonNullTypeRef,
    type_ref_from_graphql,
)
from nabu.model.symbols import (
    EnumTypeSymbol,
    FieldSymbol,
    InputTypeSymbol,
    InterfaceTypeSymbol,
    ObjectTypeSymbol,
    OperationSymbol,
    ScalarTypeSymbol,
    Symbol,
    UnionTypeSymbol,
    VariableSymbol,
)


def _unwrap_field(gql_type) -> tuple[str, bool, bool]:
    type_ref = type_ref_from_graphql(gql_type)

    non_null = isinstance(type_ref, NonNullTypeRef)
    if non_null:
        type_ref = type_ref.inner

    is_list = isinstance(type_ref, ListTypeRef)
    if is_list:
        type_ref = type_ref.item
        if isinstance(type_ref, NonNullTypeRef):
            type_ref = type_ref.inner

    name = type_ref.name if isinstance(type_ref, NamedTypeRef) else str(type_ref)
    return name, non_null, is_list


def _build_fields(gql_fields: dict) -> list[FieldSymbol]:
    result = []
    for field_name, field_definition in gql_fields.items():
        type_name, non_null, is_list = _unwrap_field(field_definition.type)
        result.append(
            FieldSymbol(
                name=field_name, type_name=type_name, non_null=non_null, is_list=is_list
            )
        )
    return result


def _build_variable(var_node) -> VariableSymbol:
    var_type = var_node.type
    non_null = var_type.__class__.__name__ == "NonNullTypeNode"
    if non_null:
        var_type = var_type.type
    type_name = var_type.name.value if hasattr(var_type, "name") else str(var_type)
    return VariableSymbol(
        name=var_node.variable.name.value, type_name=type_name, non_null=non_null
    )


def _schema_to_symbols(
    schema: GraphQLSchema, diagnostics: list[Diagnostic]
) -> dict[str, Symbol]:
    symbols: dict[str, Symbol] = {}
    root_types = root_type_names(schema)

    for name, var_type in schema.type_map.items():
        if is_builtin(name) or name in root_types:
            continue

        if name in symbols:
            diagnostics.append(
                Diagnostic(
                    code=ErrorCode.DUPLICATE_TYPE,
                    severity="error",
                    message=f"Duplicate type definition: {name}",
                )
            )
            continue

        if isinstance(var_type, GraphQLObjectType):
            symbols[name] = ObjectTypeSymbol(
                name=name,
                fields=_build_fields(var_type.fields),
                interfaces=[i.name for i in var_type.interfaces],
            )
        elif isinstance(var_type, GraphQLInputObjectType):
            symbols[name] = InputTypeSymbol(
                name=name, fields=_build_fields(var_type.fields)
            )
        elif isinstance(var_type, GraphQLEnumType):
            symbols[name] = EnumTypeSymbol(
                name=name, values=[v for v in var_type.values]
            )
        elif isinstance(var_type, GraphQLScalarType):
            symbols[name] = ScalarTypeSymbol(name=name, builtin=name in BUILTIN_SCALARS)
        elif isinstance(var_type, GraphQLInterfaceType):
            symbols[name] = InterfaceTypeSymbol(
                name=name, fields=_build_fields(var_type.fields)
            )
        elif isinstance(var_type, GraphQLUnionType):
            symbols[name] = UnionTypeSymbol(
                name=name, members=[m.name for m in var_type.types]
            )

    return symbols


def _documents_to_operations(
    documents: list[DocumentNode],
    diagnostics: list[Diagnostic],
) -> dict[str, OperationSymbol]:
    operations: dict[str, OperationSymbol] = {}

    for doc in documents:
        for node in doc.definitions:
            if not isinstance(node, OperationDefinitionNode):
                continue
            name = node.name.value if node.name else "<anonymous>"
            if name in operations:
                diagnostics.append(
                    Diagnostic(
                        code=ErrorCode.DUPLICATE_OPERATION,
                        severity="error",
                        message=f"Duplicate operation name: {name}",
                    )
                )
                continue
            operations[name] = OperationSymbol(
                name=name,
                operation_type=node.operation,
                variables=[
                    _build_variable(variable) for variable in node.variable_definitions
                ],
                selection=[
                    s.name.value
                    for s in node.selection_set.selections
                    if isinstance(s, FieldNode)
                ],
            )

    return operations


def dependency_order(table: SymbolTable) -> list[str]:
    dependencies: dict[str, set[str]] = {}
    for name, symbol in table.symbols.items():
        if isinstance(symbol, (ObjectTypeSymbol, InputTypeSymbol, InterfaceTypeSymbol)):
            dependencies[name] = {
                field.type_name
                for field in symbol.fields
                if field.type_name in table.symbols
            }
        else:
            dependencies[name] = set()

    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(symbol_name: str) -> None:
        if symbol_name in visited:
            return
        if symbol_name in visiting:
            return
        visiting.add(symbol_name)
        for dependency in dependencies.get(symbol_name, set()):
            visit(dependency)
        visiting.discard(symbol_name)
        visited.add(symbol_name)
        order.append(symbol_name)

    for name in dependencies:
        visit(name)

    return order


class SymbolTable:
    def __init__(
        self, symbols: dict[str, Symbol], operations: dict[str, OperationSymbol]
    ) -> None:
        self._symbols = symbols
        self._operations = operations

    @classmethod
    def build(
        cls, schema: GraphQLSchema, documents: list[DocumentNode]
    ) -> Result[SymbolTable]:
        diagnostics: list[Diagnostic] = []
        symbols = _schema_to_symbols(schema, diagnostics)
        operations = _documents_to_operations(documents, diagnostics)
        return Result(value=cls(symbols, operations), diagnostics=diagnostics)

    def get(self, name: str) -> Symbol | None:
        return self._symbols.get(name)

    def resolve_type(self, name: str) -> Symbol:
        symbol = self._symbols.get(name)
        if symbol is None:
            raise KeyError(f"Unknown type: {name}")
        return symbol

    def get_interfaces(self, type_name: str) -> list[InterfaceTypeSymbol]:
        symbol = self._symbols.get(type_name)
        if not isinstance(symbol, ObjectTypeSymbol):
            return []
        return [
            member_type_symbol
            for interface in symbol.interfaces
            if isinstance(
                member_type_symbol := self._symbols.get(interface), InterfaceTypeSymbol
            )
        ]

    def get_union_members(self, union_name: str) -> list[ObjectTypeSymbol]:
        symbol = self._symbols.get(union_name)
        if not isinstance(symbol, UnionTypeSymbol):
            return []
        return [
            member_type_symbol
            for member in symbol.members
            if isinstance(
                member_type_symbol := self._symbols.get(member), ObjectTypeSymbol
            )
        ]

    def get_operation(self, name: str) -> OperationSymbol:
        operation = self._operations.get(name)
        if operation is None:
            raise KeyError(f"Unknown operation: {name}")
        return operation

    def all_operations(self) -> list[OperationSymbol]:
        return list(self._operations.values())

    @property
    def symbols(self) -> dict[str, Symbol]:
        return self._symbols
