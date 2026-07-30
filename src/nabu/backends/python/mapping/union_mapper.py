from nabu.backends.python.mapping.names import to_class_name


def map_union(members: list[str]) -> str:
    return " | ".join(to_class_name(m) for m in members)
