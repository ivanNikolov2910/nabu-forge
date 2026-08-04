from nabu.ir.document import IRDocument
from nabu.ir.types import unwrap_to_named
from nabu.log import logger


def dependency_order(document: IRDocument) -> list[str]:
    logger.info(
        f"Calculating dependency order for {len(document.objects)} objects, {len(document.inputs)} inputs, and {len(document.interfaces)} interfaces..."
    )
    all_types = document.objects + document.inputs + document.interfaces
    declaration_order = [t.name for t in all_types]
    all_names = set(declaration_order)

    def field_deps(fields) -> list[str]:
        deps: list[str] = []
        for field in fields:
            named = unwrap_to_named(field.type_ref)
            if named and named.name in all_names and named.name not in deps:
                deps.append(named.name)
        return deps

    dependencies = {t.name: field_deps(t.fields) for t in all_types}

    order: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visited or name in visiting:
            return
        visiting.add(name)
        for dependency in dependencies.get(name, []):
            visit(dependency)
        visiting.discard(name)
        visited.add(name)
        order.append(name)

    for name in declaration_order:
        visit(name)
    return order
