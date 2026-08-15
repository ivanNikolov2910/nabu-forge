from dataclasses import dataclass

from nabu.analysis.index import IRIndex
from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import (
    ClassSpec,
    FieldSpec,
    UnionSpec,
    build_field_spec,
    make_typename_field,
    needs_model_config,
    wrap_annotation,
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
from nabu.ir.types import unwrap_to_named
from nabu.log import logger


@dataclass(frozen=True)
class _GenContext:
    index: IRIndex
    scalars: dict[str, str]
    enum_names: set[str]
    collector: ImportCollector
    document: IRDocument
    out_classes: list  # list[ClassSpec | UnionSpec], mutated in place


def _is_polymorphic(type_name: str, document: IRDocument) -> bool:
    union_names = {u.name for u in document.unions}
    interface_names = {i.name for i in document.interfaces}
    return type_name in union_names or type_name in interface_names


def _inline_fragments(
    selections: list[IRSelection], fragments: dict[str, IRFragment]
) -> list[IRSelection]:
    result: list[IRSelection] = []
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


def _nested_field_spec(
    wire_name: str,
    annotation: str,
    collector: ImportCollector,
    explicit_alias: bool = False,
) -> FieldSpec:
    snake = to_field_name(wire_name)
    nullable = "| None" in annotation
    if snake != wire_name or explicit_alias:
        collector.add("pydantic.Field")
        default = (
            f' = Field(None, alias="{wire_name}")'
            if nullable
            else f' = Field(..., alias="{wire_name}")'
        )
    else:
        default = " = None" if nullable else ""
    return FieldSpec(name=snake, annotation=annotation, default=default)


def _selection_fields(
    selections: list[IRSelection],
    parent_type: str,
    prefix: str,
    ctx: _GenContext,
) -> list[FieldSpec]:
    fields: list[FieldSpec] = []

    for sel in selections:
        if isinstance(sel, IRInlineFragment):
            frag_class = prefix + to_class_name(sel.on_type)
            frag_fields = _selection_fields(
                sel.selections, sel.on_type, frag_class, ctx
            )
            ctx.out_classes.append(ClassSpec(class_name=frag_class, fields=frag_fields))
            fields.append(
                FieldSpec(
                    name=to_field_name(sel.on_type),
                    annotation=f"{frag_class} | None",
                    default=" = None",
                )
            )
            continue

        if not isinstance(sel, IRFieldSelection):
            continue

        ir_field = ctx.index.field_of(parent_type, sel.name)
        if ir_field is None:
            continue

        wire_name = sel.alias or sel.name

        if not sel.selections:
            field = build_field_spec(
                ir_field,
                ctx.scalars,
                ctx.enum_names,
                ctx.collector,
                enums_module="..enums",
            )
            if sel.alias and sel.alias != ir_field.name:
                snake = to_field_name(sel.alias)
                nullable = (
                    "| None" in field.annotation
                    or field.default.startswith(" = None")
                    or "None" in field.default
                )
                ctx.collector.add("pydantic.Field")
                default = (
                    f' = Field(None, alias="{sel.alias}")'
                    if nullable
                    else f' = Field(..., alias="{sel.alias}")'
                )
                field = FieldSpec(
                    name=snake, annotation=field.annotation, default=default
                )
            fields.append(field)
            continue

        named = unwrap_to_named(ir_field.type_ref)
        child_type = named.name if named else sel.name
        child_class = prefix + to_class_name(wire_name)
        inline_frags = [s for s in sel.selections if isinstance(s, IRInlineFragment)]

        if _is_polymorphic(child_type, ctx.document) and inline_frags:
            ctx.collector.add("typing.Literal")
            ctx.collector.add("typing.Annotated")
            ctx.collector.add("pydantic.Field")
            ctx.collector.add("pydantic.ConfigDict")
            shared_sels = [s for s in sel.selections if isinstance(s, IRFieldSelection)]
            member_names: list[str] = []
            for frag in inline_frags:
                member_class = child_class + to_class_name(frag.on_type)
                frag_fields = [make_typename_field(frag.on_type)] + _selection_fields(
                    shared_sels + list(frag.selections), frag.on_type, member_class, ctx
                )
                ctx.out_classes.append(
                    ClassSpec(
                        class_name=member_class, fields=frag_fields, has_aliases=True
                    )
                )
                member_names.append(member_class)
            ctx.out_classes.append(
                UnionSpec(alias_name=child_class, member_classes=member_names)
            )
        else:
            child_fields = _selection_fields(
                sel.selections, child_type, child_class, ctx
            )
            has_aliases = needs_model_config(child_fields)
            if has_aliases:
                ctx.collector.add("pydantic.ConfigDict")
            ctx.out_classes.append(
                ClassSpec(
                    class_name=child_class, fields=child_fields, has_aliases=has_aliases
                )
            )

        annotation = wrap_annotation(ir_field.type_ref, child_class)
        fields.append(
            _nested_field_spec(
                wire_name,
                annotation,
                ctx.collector,
                explicit_alias=sel.alias is not None,
            )
        )

    return fields


def generate_operation(
    operation: IROperation, document: IRDocument, config: Config
) -> str:
    logger.debug("Generating operation model for %s", operation.name)
    collector = ImportCollector()
    fragments = {f.name: f for f in document.fragments}

    root_type = (
        "Query" if operation.operation_type == IROperationType.QUERY else "Mutation"
    )
    prefix = to_class_name(operation.name)

    classes: list[ClassSpec | UnionSpec] = []
    ctx = _GenContext(
        index=IRIndex(document),
        scalars=scalar_table(config.scalars),
        enum_names={e.name for e in document.enums},
        collector=collector,
        document=document,
        out_classes=classes,
    )
    result_fields = _selection_fields(
        _inline_fragments(operation.selections, fragments), root_type, prefix, ctx
    )

    result_has_aliases = needs_model_config(result_fields)
    if result_has_aliases:
        collector.add("pydantic.ConfigDict")

    return render(
        "operation_model.py.jinja",
        {
            "classes": classes,
            "result_class": f"{prefix}Result",
            "result_fields": result_fields,
            "result_has_aliases": result_has_aliases,
            "imports": collector.render(),
        },
    )


def generate_operations(document: IRDocument, config: Config) -> dict[str, str]:
    return {
        f"{to_field_name(op.name)}.py": generate_operation(op, document, config)
        for op in document.operations
    }
