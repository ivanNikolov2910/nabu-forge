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
    all_names = {t.name for t in all_types}
    deps: dict[str, set[str]] = {
        t.name: {
            name
            for f in t.fields
            for name in _type_names(f.type_ref)
            if name in all_names
        }
        for t in all_types
    }

    order: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited or name in visiting:
            return
        visiting.add(name)
        for dep in deps.get(name, set()):
            visit(dep)
        visiting.discard(name)
        visited.add(name)
        order.append(name)

    for name in all_names:
        visit(name)
    return order
