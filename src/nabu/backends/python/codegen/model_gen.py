from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import build_fields
from nabu.backends.python.codegen.ordering import dependency_order
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config
from nabu.ir.definitions import IRInterfaceType, IRObjectType
from nabu.ir.document import IRDocument


def generate_models(document: IRDocument, config: Config) -> str:
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    enum_names = {e.name for e in document.enums}
    type_by_name: dict[str, IRObjectType | IRInterfaceType] = {
        type_definition.name: type_definition
        for type_definition in document.objects + document.interfaces
    }

    models = []
    for name in dependency_order(document):
        ir_type = type_by_name.get(name)
        if ir_type is None:
            continue
        models.append(
            {
                "class_name": to_class_name(ir_type.name),
                "fields": build_fields(ir_type.fields, scalars, enum_names, collector),
            }
        )

    return render("model.py.jinja", {"models": models, "imports": collector.render()})
