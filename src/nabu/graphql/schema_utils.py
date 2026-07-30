from graphql import GraphQLSchema

BUILTIN_SCALARS: frozenset[str] = frozenset({"String", "Int", "Float", "Boolean", "ID"})


def root_type_names(schema: GraphQLSchema) -> set[str]:
    return {
        t.name
        for t in (schema.query_type, schema.mutation_type, schema.subscription_type)
        if t is not None
    }


def is_builtin(name: str) -> bool:
    return name.startswith("__") or name in BUILTIN_SCALARS
