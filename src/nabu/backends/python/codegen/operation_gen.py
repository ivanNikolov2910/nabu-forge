from nabu.analysis.index import IRIndex
from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.ir.operations import (
    IRFieldSelection,
    IRFragment,
    IRFragmentSpread,
    IRInlineFragment,
    IROperation,
    IRSelection,
)
from nabu.ir.types import ListTypeRef, NamedTypeRef, NonNullTypeRef, TypeRef


def _unwrap_name(ref: TypeRef) -> str | None:
    if isinstance(ref, (NonNullTypeRef,)):
        return _unwrap_name(ref.inner)
    if isinstance(ref, ListTypeRef):
        return _unwrap_name(ref.item)
    if isinstance(ref, NamedTypeRef):
        return ref.name
    return None


def _inline_fragments(
    selections: list[IRSelection],
    fragments: dict[str, IRFragment],
) -> list[IRSelection]:
    result = []
    for sel in selections:
        if isinstance(sel, IRFragmentSpread):
            frag = fragments.get(sel.name)
            if frag:
                result.extend(_inline_fragments(frag.selections, fragments))
        elif isinstance(sel, IRFieldSelection):
            result.append(
                IRFieldSelection(
                    name=sel.name,
                    alias=sel.alias,
                    arguments=sel.arguments,
                    selections=_inline_fragments(sel.selections, fragments),
                    source_location=sel.source_location,
                )
            )
        elif isinstance(sel, IRInlineFragment):
            result.append(
                IRInlineFragment(
                    on_type=sel.on_type,
                    selections=_inline_fragments(sel.selections, fragments),
                )
            )
        else:
            result.append(sel)
    return result


def _build_selection_classes(
    selections: list[IRSelection],
    parent_type: str,
    prefix: str,
    index: IRIndex,
    scalars: dict[str, str],
    collector: ImportCollector,
    classes: list[dict],
    enum_names: set[str],
) -> list[dict]:
    fields = []
    for sel in selections:
        if not isinstance(sel, IRFieldSelection):
            continue

        field_name = sel.alias or sel.name
        ir_field = index.field_of(parent_type, sel.name)
        if ir_field is None:
            continue

        if sel.selections:
            child_class = prefix + to_class_name(sel.name)
            child_type = _unwrap_name(ir_field.type_ref) or sel.name
            _build_selection_classes(
                sel.selections,
                child_type,
                child_class,
                index,
                scalars,
                collector,
                classes,
                enum_names,
            )
            nullable = not isinstance(ir_field.type_ref, NonNullTypeRef)
            annotation = child_class + (" | None" if nullable else "")
            fields.append(
                {
                    "name": to_field_name(field_name),
                    "annotation": annotation,
                    "nullable": nullable,
                }
            )
        else:
            annotation = map_type(ir_field.type_ref, scalars)
            ref = ir_field.type_ref
            while isinstance(ref, (NonNullTypeRef, ListTypeRef)):
                ref = ref.inner if isinstance(ref, NonNullTypeRef) else ref.item
            if isinstance(ref, NamedTypeRef) and ref.name in enum_names:
                collector.add_relative("enums", to_class_name(ref.name))
            else:
                collector.add(annotation)
            fields.append(
                {
                    "name": to_field_name(field_name),
                    "annotation": annotation,
                    "nullable": not isinstance(ir_field.type_ref, NonNullTypeRef),
                }
            )

    classes.append({"class_name": prefix, "fields": fields})
    return fields


def generate_operation(
    operation: IROperation,
    document: IRDocument,
    config: Config,
) -> str:
    from graphql import OperationType

    scalars = scalar_table(config.scalars)
    index = IRIndex(document)
    collector = ImportCollector()
    fragments = {f.name: f for f in document.fragments}
    enum_names = {e.name for e in document.enums}

    root_type = (
        "Query" if operation.operation_type == OperationType.QUERY else "Mutation"
    )
    prefix = to_class_name(operation.name)

    inlined = _inline_fragments(operation.selections, fragments)
    classes: list[dict] = []
    result_fields = _build_selection_classes(
        inlined, root_type, prefix, index, scalars, collector, classes, enum_names
    )
    if classes:
        classes.pop()

    return render(
        "operation_model.py.jinja",
        {
            "classes": classes,
            "result_class": f"{prefix}Result",
            "result_fields": result_fields,
            "imports": collector.render(),
        },
    )


def generate_operations(document: IRDocument, config: Config) -> dict[str, str]:
    return {
        f"{operation.name.lower()}.py": generate_operation(operation, document, config)
        for operation in document.operations
    }
