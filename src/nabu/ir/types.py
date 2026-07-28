from __future__ import annotations

from dataclasses import dataclass

from graphql import GraphQLList, GraphQLNonNull, GraphQLType


@dataclass(frozen=True)
class NamedTypeRef:
    name: str


@dataclass(frozen=True)
class ListTypeRef:
    item: TypeRef


@dataclass(frozen=True)
class NonNullTypeRef:
    inner: TypeRef


TypeRef = NamedTypeRef | ListTypeRef | NonNullTypeRef


def type_ref_from_graphql(gql_type: GraphQLType) -> TypeRef:
    """Recursively convert a graphql-core type into an IR TypeRef.

    Handles arbitrary nesting of NonNull and List wrappers, e.g. [[Int!]]!.
    """
    if isinstance(gql_type, GraphQLNonNull):
        return NonNullTypeRef(inner=type_ref_from_graphql(gql_type.of_type))
    if isinstance(gql_type, GraphQLList):
        return ListTypeRef(item=type_ref_from_graphql(gql_type.of_type))
    return NamedTypeRef(name=gql_type.name)
