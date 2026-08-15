from nabu.backends.python.codegen.engine import render
from nabu.backends.python.codegen.fields import build_class_spec
from nabu.backends.python.mapping.imports import ImportCollector
from nabu.backends.python.mapping.scalars import scalar_table
from nabu.config.loader import Config
from nabu.ir.document import IRDocument
from nabu.log import logger


def generate_inputs(document: IRDocument, config: Config) -> str:
    logger.debug("Generating %d inputs", len(document.inputs))
    scalars = scalar_table(config.scalars)
    collector = ImportCollector()
    enum_names = {e.name for e in document.enums}
    models = [
        build_class_spec(input_, scalars, enum_names, collector)
        for input_ in document.inputs
    ]
    return render("input.py.jinja", {"models": models, "imports": collector.render()})
