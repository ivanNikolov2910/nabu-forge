from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name, to_field_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.backends.python.mapping.type_mapper import map_type
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.ir.types import NonNullTypeRef


def generate_inputs(document: IRDocument, config: Config) -> str:
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    models = []
    for input_ in document.inputs:
        fields = []
        for f in input_.fields:
            annotation = map_type(f.type_ref, scalars)
            collector.add(annotation)
            fields.append(
                {
                    "name": to_field_name(f.name),
                    "annotation": annotation,
                    "nullable": not isinstance(f.type_ref, NonNullTypeRef),
                }
            )
        models.append(
            {
                "class_name": to_class_name(input_.name),
                "fields": fields,
            }
        )
    return render("input.py.jinja", {"models": models, "imports": collector.render()})
