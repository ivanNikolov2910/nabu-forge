from __future__ import annotations

from graphql import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLUnionType,
    InlineFragmentNode,
    ListTypeNode,
    NonNullTypeNode,
    OperationDefinitionNode,
    SelectionSetNode,
    TypeNode,
    Undefined,
    VariableNode,
)
from graphql.utilities import value_from_ast_untyped

from nabu.config.types import is_builtin_scalar, root_type_names
from nabu.diagnostics.result import Result
from nabu.ir.definitions import (
    IRArgument,
    IREnumType,
    IRField,
    IRInputType,
    IRInterfaceType,
    IRObjectType,
    IRScalarType,
    IRUnionType,
)
from nabu.ir.document import IRDocument
from nabu.ir.location import SourceLocation, source_location_from_node
from nabu.ir.operations import (
    IRArgumentValue,
    IRFieldSelection,
    IRFragment,
    IRFragmentSpread,
    IRInlineFragment,
    IROperation,
    IRSelection,
    IRVariable,
    IRVariableRef,
)
from nabu.ir.types import (
    ListTypeRef,
    NamedTypeRef,
    NonNullTypeRef,
    TypeRef,
    type_ref_from_graphql,
)


def _field_arguments(gql_field) -> list[IRArgument]:
    # Input fields (GraphQLInputField) have no arguments; only output fields do.
    args = getattr(gql_field, "args", None)
    if not args:
        return []
    return [
        IRArgument(
            name=arg_name,
            type_ref=type_ref_from_graphql(arg.type),
            default_value=(
                None if arg.default_value is Undefined else arg.default_value
            ),
        )
        for arg_name, arg in args.items()
    ]


def _ir_fields(gql_fields: dict) -> list[IRField]:
    return [
        IRField(
            name=name,
            type_ref=type_ref_from_graphql(gql_field.type),
            arguments=_field_arguments(gql_field),
            source_location=source_location_from_node(
                getattr(gql_field, "ast_node", None)
            ),
        )
        for name, gql_field in gql_fields.items()
    ]


def _type_loc(gql_type) -> SourceLocation | None:
    return source_location_from_node(getattr(gql_type, "ast_node", None))


def _build_definitions(schema: GraphQLSchema, doc: IRDocument) -> None:
    root_types = root_type_names(schema)
    for name, gql_type in schema.type_map.items():
        if is_builtin_scalar(name) or name in root_types:
            continue

        if isinstance(gql_type, GraphQLObjectType):
            doc.objects.append(
                IRObjectType(
                    name=name,
                    fields=_ir_fields(gql_type.fields),
                    interfaces=[i.name for i in gql_type.interfaces],
                    source_location=_type_loc(gql_type),
                )
            )
        elif isinstance(gql_type, GraphQLInputObjectType):
            doc.inputs.append(
                IRInputType(
                    name=name,
                    fields=_ir_fields(gql_type.fields),
                    source_location=_type_loc(gql_type),
                )
            )
        elif isinstance(gql_type, GraphQLEnumType):
            doc.enums.append(
                IREnumType(
                    name=name,
                    values=list(gql_type.values),
                    source_location=_type_loc(gql_type),
                )
            )
        elif isinstance(gql_type, GraphQLScalarType):
            doc.scalars.append(
                IRScalarType(
                    name=name,
                    builtin=is_builtin_scalar(name),
                    source_location=_type_loc(gql_type),
                )
            )
        elif isinstance(gql_type, GraphQLInterfaceType):
            doc.interfaces.append(
                IRInterfaceType(
                    name=name,
                    fields=_ir_fields(gql_type.fields),
                    source_location=_type_loc(gql_type),
                )
            )
        elif isinstance(gql_type, GraphQLUnionType):
            doc.unions.append(
                IRUnionType(
                    name=name,
                    members=[m.name for m in gql_type.types],
                    source_location=_type_loc(gql_type),
                )
            )


def _type_ref_from_ast(type_node: TypeNode) -> TypeRef:
    if isinstance(type_node, NonNullTypeNode):
        return NonNullTypeRef(inner=_type_ref_from_ast(type_node.type))
    if isinstance(type_node, ListTypeNode):
        return ListTypeRef(item=_type_ref_from_ast(type_node.type))
    return NamedTypeRef(name=type_node.name.value)


def _argument_value(value_node) -> object:
    if isinstance(value_node, VariableNode):
        return IRVariableRef(name=value_node.name.value)
    return value_from_ast_untyped(value_node)


def _argument_values(node: FieldNode) -> list[IRArgumentValue]:
    return [
        IRArgumentValue(name=arg.name.value, value=_argument_value(arg.value))
        for arg in node.arguments
    ]


def _selection(node) -> IRSelection:
    if isinstance(node, FieldNode):
        return IRFieldSelection(
            name=node.name.value,
            alias=node.alias.value if node.alias else None,
            arguments=_argument_values(node),
            selections=_selections(node.selection_set),
            source_location=source_location_from_node(node),
        )
    if isinstance(node, InlineFragmentNode):
        return IRInlineFragment(
            on_type=node.type_condition.name.value,
            selections=_selections(node.selection_set),
        )
    if isinstance(node, FragmentSpreadNode):
        return IRFragmentSpread(name=node.name.value)
    raise TypeError(f"Unsupported selection node: {type(node).__name__}")


def _selections(selection_set: SelectionSetNode | None) -> list[IRSelection]:
    if selection_set is None:
        return []
    return [_selection(sel) for sel in selection_set.selections]


def _variable(var_node) -> IRVariable:
    return IRVariable(
        name=var_node.variable.name.value,
        type_ref=_type_ref_from_ast(var_node.type),
        default_value=(
            value_from_ast_untyped(var_node.default_value)
            if var_node.default_value
            else None
        ),
    )


def _build_operations(documents: list[DocumentNode], doc: IRDocument) -> None:
    for document in documents:
        for node in document.definitions:
            if isinstance(node, OperationDefinitionNode):
                doc.operations.append(
                    IROperation(
                        name=node.name.value if node.name else "<anonymous>",
                        operation_type=node.operation,
                        variables=[_variable(v) for v in node.variable_definitions],
                        selections=_selections(node.selection_set),
                        source_location=source_location_from_node(node),
                    )
                )
            elif isinstance(node, FragmentDefinitionNode):
                doc.fragments.append(
                    IRFragment(
                        name=node.name.value,
                        on_type=node.type_condition.name.value,
                        selections=_selections(node.selection_set),
                    )
                )


def build_ir(
    schema: GraphQLSchema, documents: list[DocumentNode]
) -> Result[IRDocument]:
    doc = IRDocument(
        objects=[],
        inputs=[],
        enums=[],
        scalars=[],
        interfaces=[],
        unions=[],
        operations=[],
        fragments=[],
    )
    _build_definitions(schema, doc)
    _build_operations(documents, doc)
    return Result(value=doc, diagnostics=[])
