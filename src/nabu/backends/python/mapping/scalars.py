BUILTIN_SCALAR_ANNOTATIONS: dict[str, str] = {
    "ID": "str",
    "String": "str",
    "Int": "int",
    "Float": "float",
    "Boolean": "bool",
}


def scalar_table(config_scalars: dict[str, str]) -> dict[str, str]:
    return {**BUILTIN_SCALAR_ANNOTATIONS, **config_scalars}
