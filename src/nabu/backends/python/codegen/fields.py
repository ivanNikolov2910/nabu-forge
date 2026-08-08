from dataclasses import dataclass

from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.ir.definitions import IRField
from nabu.ir.types import ListTypeRef, NonNullTypeRef, TypeRef, unwrap_to_named


@dataclass(frozen=True)
class FieldSpec:
    name: str
    annotation: str
    default: str


@dataclass(frozen=True)
class ClassSpec:
    class_name: str
    fields: list[FieldSpec]
    has_aliases: bool = False


@dataclass(frozen=True)
class UnionSpec:
    alias_name: str
    member_classes: list[str]


def make_typename_field(concrete_type_name: str) -> FieldSpec:
    return FieldSpec(
        name="typename",
        annotation=f'Literal["{concrete_type_name}"]',
        default=' = Field(alias="__typename")',
    )


def wrap_annotation(type_ref: TypeRef, leaf: str) -> str:
    def _inner(ref: TypeRef) -> str:
        if isinstance(ref, NonNullTypeRef):
            return _non_null(ref.inner)
        return f"{_non_null(ref)} | None"

    def _non_null(ref: TypeRef) -> str:
        if isinstance(ref, NonNullTypeRef):
            return _non_null(ref.inner)
        if isinstance(ref, ListTypeRef):
            return f"list[{_inner(ref.item)}]"
        return leaf

    return _inner(type_ref)


def build_field(
    ir_field: IRField,
    scalars: dict[str, str],
    enum_names: set[str],
    collector: ImportCollector,
    enums_module: str = "enums",
) -> FieldSpec:
    annotation = map_type(ir_field.type_ref, scalars)
    named = unwrap_to_named(ir_field.type_ref)
    if named is not None and named.name in enum_names:
        collector.add_relative(enums_module, to_class_name(named.name))
    else:
        annotation = collector.add(annotation)
    nullable = not isinstance(ir_field.type_ref, NonNullTypeRef)

    snake = to_field_name(ir_field.name)
    if snake != ir_field.name:
        collector.add("pydantic.Field")
        default = (
            f' = Field(None, alias="{ir_field.name}")'
            if nullable
            else f' = Field(..., alias="{ir_field.name}")'
        )
    else:
        default = " = None" if nullable else ""

    return FieldSpec(name=snake, annotation=annotation, default=default)


def build_fields(
    ir_fields: list[IRField],
    scalars: dict[str, str],
    enum_names: set[str],
    collector: ImportCollector,
    enums_module: str = "enums",
) -> list[FieldSpec]:
    return [
        build_field(f, scalars, enum_names, collector, enums_module) for f in ir_fields
    ]


def needs_model_config(fields: list[FieldSpec]) -> bool:
    return any("alias=" in f.default for f in fields)
