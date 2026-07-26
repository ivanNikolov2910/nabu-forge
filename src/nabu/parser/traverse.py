from dataclasses import dataclass

from graphql.type.definition import *
from graphql.type.schema import GraphQLSchema

_BUILTIN_SCALARS = {"String", "Int", "Float", "Boolean", "ID"}


def _is_builtin(name: str) -> bool:
    return name.startswith("__") or name in _BUILTIN_SCALARS


@dataclass
class SchemaSummary:
    object_types: list[str]
    input_types: list[str]
    enums: list[str]
    scalars: list[str]
    interfaces: list[str]
    unions: list[str]
    queries: list[str]
    mutations: list[str]


def summarise(schema: GraphQLSchema) -> SchemaSummary:
    object_types, input_types, enums, scalars, interfaces, unions = (
        [],
        [],
        [],
        [],
        [],
        [],
    )

    for name, named_type in schema.type_map.items():
        if _is_builtin(name):
            continue
        if isinstance(named_type, GraphQLObjectType) and name not in (
            "Query",
            "Mutation",
            "Subscription",
        ):
            object_types.append(name)
        elif isinstance(named_type, GraphQLInputObjectType):
            input_types.append(name)
        elif isinstance(named_type, GraphQLEnumType):
            enums.append(name)
        elif isinstance(named_type, GraphQLScalarType):
            scalars.append(name)
        elif isinstance(named_type, GraphQLInterfaceType):
            interfaces.append(name)
        elif isinstance(named_type, GraphQLUnionType):
            unions.append(name)

    queries = list(schema.query_type.fields) if schema.query_type else []
    mutations = list(schema.mutation_type.fields) if schema.mutation_type else []

    return SchemaSummary(
        object_types=sorted(object_types),
        input_types=sorted(input_types),
        enums=sorted(enums),
        scalars=sorted(scalars),
        interfaces=sorted(interfaces),
        unions=sorted(unions),
        queries=sorted(queries),
        mutations=sorted(mutations),
    )
