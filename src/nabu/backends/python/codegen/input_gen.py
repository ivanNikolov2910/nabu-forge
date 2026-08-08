from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import (
    ClassSpec,
    build_fields,
    needs_model_config,
)
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.names import to_class_name
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.log import logger


def generate_inputs(document: IRDocument, config: Config) -> str:
    logger.debug("Generating %d inputs", len(document.inputs))
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    enum_names = {e.name for e in document.enums}
    models = []
    for input_ in document.inputs:
        fields = build_fields(input_.fields, scalars, enum_names, collector)
        has_aliases = needs_model_config(fields)
        if has_aliases:
            collector.add("pydantic.ConfigDict")
        models.append(
            ClassSpec(
                class_name=to_class_name(input_.name),
                fields=fields,
                has_aliases=has_aliases,
            )
        )
    return render("input.py.jinja", {"models": models, "imports": collector.render()})
