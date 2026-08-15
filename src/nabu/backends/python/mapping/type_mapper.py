from nabu.ir.types import ListTypeRef, NonNullTypeRef, TypeRef


def _resolve(ref: TypeRef, scalars: dict[str, str]) -> str:
    if isinstance(ref, NonNullTypeRef):
        return _resolve(ref.inner, scalars)
    if isinstance(ref, ListTypeRef):
        return f"list[{map_type(ref.item, scalars)}]"
    return scalars.get(ref.name, ref.name)


def map_type(ref: TypeRef, scalars: dict[str, str]) -> str:
    if isinstance(ref, NonNullTypeRef):
        return _resolve(ref.inner, scalars)
    return f"{_resolve(ref, scalars)} | None"
