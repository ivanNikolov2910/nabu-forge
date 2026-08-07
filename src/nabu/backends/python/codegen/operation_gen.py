from nabu.analysis.index import IRIndex
from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import (
    ClassSpec,
    FieldSpec,
    UnionSpec,
    build_field,
    make_typename_field,
)
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.ir.operations import (
    IRFieldSelection,
    IRFragment,
    IRFragmentSpread,
    IRInlineFragment,
    IROperation,
    IROperationType,
    IRSelection,
)
from nabu.ir.types import NonNullTypeRef, unwrap_to_named
from nabu.log import logger


def _is_polymorphic(type_name: str, document: IRDocument) -> bool:
    union_names = {u.name for u in document.unions}
    interface_names = {i.name for i in document.interfaces}
    return type_name in union_names or type_name in interface_names


def _inline_fragments(
    selections: list[IRSelection], fragments: dict[str, IRFragment]
) -> list[IRSelection]:
    result: list[IRSelection] = []
    for selection in selections:
        if isinstance(selection, IRFragmentSpread):
            fragment = fragments.get(selection.name)
            if fragment:
                result.extend(_inline_fragments(fragment.selections, fragments))
        elif isinstance(selection, IRFieldSelection):
            result.append(
                IRFieldSelection(
                    name=selection.name,
                    alias=selection.alias,
                    arguments=selection.arguments,
                    selections=_inline_fragments(selection.selections, fragments),
                    source_location=selection.source_location,
                )
            )
        elif isinstance(selection, IRInlineFragment):
            result.append(
                IRInlineFragment(
                    on_type=selection.on_type,
                    selections=_inline_fragments(selection.selections, fragments),
                )
            )
        else:
            result.append(selection)
    return result


def _selection_fields(
    selections: list[IRSelection],
    parent_type: str,
    prefix: str,
    index: IRIndex,
    scalars: dict[str, str],
    enum_names: set[str],
    collector: ImportCollector,
    out_classes: list[ClassSpec | UnionSpec],
    document: IRDocument,
) -> list[FieldSpec]:
    fields: list[FieldSpec] = []

    for selection in selections:
        if not isinstance(selection, IRFieldSelection):
            continue
        ir_field = index.field_of(parent_type, selection.name)
        if ir_field is None:
            continue
        field_name = selection.alias or selection.name

        if selection.selections:
            named = unwrap_to_named(ir_field.type_ref)
            child_type = named.name if named else selection.name
            child_class_name = prefix + to_class_name(field_name)
            nullable = not isinstance(ir_field.type_ref, NonNullTypeRef)

            inline_frags = [
                inline_selection
                for inline_selection in selection.selections
                if isinstance(inline_selection, IRInlineFragment)
            ]
            is_polymorphic = _is_polymorphic(child_type, document) and inline_frags

            if is_polymorphic:
                member_names: list[str] = []
                for fragment in inline_frags:
                    member_class = (
                        prefix
                        + to_class_name(field_name)
                        + to_class_name(fragment.on_type)
                    )
                    collector.add("typing.Literal")
                    collector.add("pydantic.Field")
                    collector.add("pydantic.ConfigDict")
                    fragment_fields = [
                        make_typename_field(fragment.on_type)
                    ] + _selection_fields(
                        fragment.selections,
                        fragment.on_type,
                        member_class,
                        index,
                        scalars,
                        enum_names,
                        collector,
                        out_classes,
                        document,
                    )
                    out_classes.append(
                        ClassSpec(
                            class_name=member_class,
                            fields=fragment_fields,
                            has_typename=True,
                        )
                    )
                    member_names.append(member_class)

                collector.add("typing.Annotated")
                collector.add("pydantic.Field")
                alias_name = child_class_name
                out_classes.append(
                    UnionSpec(
                        alias_name=alias_name,
                        member_classes=member_names,
                    )
                )
                annotation = alias_name + (" | None" if nullable else "")
                fields.append(
                    FieldSpec(
                        name=to_field_name(field_name),
                        annotation=annotation,
                        default=" = None" if nullable else "",
                    )
                )

            else:
                child_fields = _selection_fields(
                    selection.selections,
                    child_type,
                    child_class_name,
                    index,
                    scalars,
                    enum_names,
                    collector,
                    out_classes,
                    document,
                )
                out_classes.append(
                    ClassSpec(class_name=child_class_name, fields=child_fields)
                )
                annotation = child_class_name + (" | None" if nullable else "")
                fields.append(
                    FieldSpec(
                        name=to_field_name(field_name),
                        annotation=annotation,
                        default=" = None" if nullable else "",
                    )
                )
        else:
            fields.append(
                build_field(
                    ir_field, scalars, enum_names, collector, enums_module="..enums"
                )
            )

    for selection in selections:
        if not isinstance(selection, IRInlineFragment):
            continue
        frag_class = prefix + to_class_name(selection.on_type)
        fragment_fields = _selection_fields(
            selection.selections,
            selection.on_type,
            frag_class,
            index,
            scalars,
            enum_names,
            collector,
            out_classes,
            document,
        )
        out_classes.append(ClassSpec(class_name=frag_class, fields=fragment_fields))
        fields.append(
            FieldSpec(
                name=to_field_name(selection.on_type),
                annotation=f"{frag_class} | None",
                default=" = None",
            )
        )

    return fields


def generate_operation(
    operation: IROperation, document: IRDocument, config: Config
) -> str:
    logger.debug("Generating operation model for %s", operation.name)
    scalars = scalar_table(config.scalars)
    index = IRIndex(document)
    collector = ImportCollector()
    fragments = {fragment.name: fragment for fragment in document.fragments}
    enum_names = {enum_.name for enum_ in document.enums}

    root_type = (
        "Query" if operation.operation_type == IROperationType.QUERY else "Mutation"
    )
    prefix = to_class_name(operation.name)

    inlined = _inline_fragments(operation.selections, fragments)
    classes: list[ClassSpec | UnionSpec] = []
    result_fields = _selection_fields(
        inlined,
        root_type,
        prefix,
        index,
        scalars,
        enum_names,
        collector,
        classes,
        document,
    )

    class_entries = []
    for entry in classes:
        if isinstance(entry, ClassSpec):
            class_entries.append(
                {
                    "kind": "class",
                    "class_name": entry.class_name,
                    "fields": entry.fields,
                    "has_typename": entry.has_typename,
                }
            )
        else:
            class_entries.append(
                {
                    "kind": "union",
                    "alias_name": entry.alias_name,
                    "members": entry.member_classes,
                }
            )

    return render(
        "operation_model.py.jinja",
        {
            "classes": class_entries,
            "result_class": f"{prefix}Result",
            "result_fields": result_fields,
            "imports": collector.render(),
        },
    )


def generate_operations(document: IRDocument, config: Config) -> dict[str, str]:
    return {
        f"{to_field_name(operation.name)}.py": generate_operation(
            operation, document, config
        )
        for operation in document.operations
    }
