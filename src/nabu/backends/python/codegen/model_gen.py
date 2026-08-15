from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import build_class_spec
from nabu.backends.python.codegen.ordering import dependency_order
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config
from nabu.ir.definitions import IRInterfaceType, IRObjectType
from nabu.ir.document import IRDocument
from nabu.log import logger


def generate_models(document: IRDocument, config: Config) -> str:
    logger.debug("Generating %d models", len(document.objects))
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    enum_names = {e.name for e in document.enums}
    type_by_name: dict[str, IRObjectType | IRInterfaceType] = {
        t.name: t for t in document.objects + document.interfaces
    }

    models = []
    for name in dependency_order(document):
        ir_type = type_by_name.get(name)
        if ir_type is None:
            continue
        models.append(build_class_spec(ir_type, scalars, enum_names, collector))

    union_aliases = [
        {
            "name": to_class_name(u.name),
            "members": " | ".join(to_class_name(m) for m in u.members),
        }
        for u in document.unions
    ]

    return render(
        "model.py.jinja",
        {
            "models": models,
            "union_aliases": union_aliases,
            "imports": collector.render(),
        },
    )
