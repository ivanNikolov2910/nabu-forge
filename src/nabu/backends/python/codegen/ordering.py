from nabu.ir.document import IRDocument
from nabu.ir.types import ListTypeRef, NamedTypeRef, NonNullTypeRef, TypeRef


def _type_names(ref: TypeRef) -> set[str]:
    if isinstance(ref, NamedTypeRef):
        return {ref.name}
    if isinstance(ref, NonNullTypeRef):
        return _type_names(ref.inner)
    if isinstance(ref, ListTypeRef):
        return _type_names(ref.item)
    return set()


def dependency_order(document: IRDocument) -> list[str]:
    all_types = document.objects + document.inputs + document.interfaces
    all_names = {type_ref.name for type_ref in all_types}
    dependencies: dict[str, set[str]] = {
        type_ref.name: {
            name
            for field in type_ref.fields
            for name in _type_names(field.type_ref)
            if name in all_names
        }
        for type_ref in all_types
    }

    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited or name in visiting:
            return
        visiting.add(name)
        for dependency in dependencies.get(name, set()):
            visit(dependency)
        visiting.discard(name)
        visited.add(name)
        order.append(name)

    for name in all_names:
        visit(name)
    return order
