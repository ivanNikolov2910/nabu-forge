from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.ir.types import ListTypeRef, NamedTypeRef, NonNullTypeRef


def generate_inputs(document: IRDocument, config: Config) -> str:
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    enum_names = {e.name for e in document.enums}
    models = []
    for input_ in document.inputs:
        fields = []
        for f in input_.fields:
            annotation = map_type(f.type_ref, scalars)
            ref = f.type_ref
            while isinstance(ref, (NonNullTypeRef, ListTypeRef)):
                ref = ref.inner if isinstance(ref, NonNullTypeRef) else ref.item
            if isinstance(ref, NamedTypeRef) and ref.name in enum_names:
                collector.add_relative("enums", to_class_name(ref.name))
            else:
                annotation = collector.add(annotation)
            fields.append(
                {
                    "name": to_field_name(f.name),
                    "annotation": annotation,
                    "default": "" if isinstance(f.type_ref, NonNullTypeRef) else " = None",
                }
            )
        models.append(
            {
                "class_name": to_class_name(input_.name),
                "fields": fields,
            }
        )
    return render("input.py.jinja", {"models": models, "imports": collector.render()})
