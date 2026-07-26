from dataclasses import dataclass

from graphql.type.definition import *
from graphql.type.schema import GraphQLSchema

from nabu.config.types import is_builtin_scalar, root_type_names


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
    root_types = root_type_names(schema)

    for name, named_type in schema.type_map.items():
        if is_builtin_scalar(name) or name in root_types:
            continue
        if isinstance(named_type, GraphQLObjectType):
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
