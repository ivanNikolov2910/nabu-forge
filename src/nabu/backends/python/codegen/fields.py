from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.ir.definitions import IRField
from nabu.ir.types import ListTypeRef, NamedTypeRef, NonNullTypeRef


def build_fields(
    ir_fields: list[IRField],
    scalars: dict[str, str],
    enum_names: set[str],
    collector: ImportCollector,
) -> list[dict]:
    fields = []
    for field in ir_fields:
        annotation = map_type(field.type_ref, scalars)
        ref = field.type_ref
        while isinstance(ref, (NonNullTypeRef, ListTypeRef)):
            ref = ref.inner if isinstance(ref, NonNullTypeRef) else ref.item
        if isinstance(ref, NamedTypeRef) and ref.name in enum_names:
            collector.add_relative("enums", to_class_name(ref.name))
        else:
            annotation = collector.add(annotation)
        fields.append(
            {
                "name": to_field_name(field.name),
                "annotation": annotation,
                "default": ""
                if isinstance(field.type_ref, NonNullTypeRef)
                else " = None",
            }
        )
    return fields
