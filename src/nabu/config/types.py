from graphql import GraphQLSchema

REQUIRED_FIELDS = ("schema", "operations", "output")
BUILTIN_SCALARS = {"String", "Int", "Float", "Boolean", "ID"}


def root_type_names(schema: GraphQLSchema) -> set[str]:
    return {
        root_type.name
        for root_type in (
            schema.query_type,
            schema.mutation_type,
            schema.subscription_type,
        )
        if root_type is not None
    }


def is_builtin_scalar(name: str) -> bool:
    return name.startswith("__") or name in BUILTIN_SCALARS
