from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import ClassSpec, build_fields
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config
from nabu.ir.document import IRDocument


def generate_inputs(document: IRDocument, config: Config) -> str:
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    enum_names = {e.name for e in document.enums}
    models = [
        ClassSpec(
            class_name=to_class_name(input_.name),
            fields=build_fields(input_.fields, scalars, enum_names, collector),
        )
        for input_ in document.inputs
    ]
    return render("input.py.jinja", {"models": models, "imports": collector.render()})
