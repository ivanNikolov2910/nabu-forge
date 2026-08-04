from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.names import to_class_name
from nabu.ir.document import IRDocument
from nabu.log import logger


def generate_enums(document: IRDocument) -> str:
    logger.info(f"Generating {len(document.enums)} enums...")
    enums = [
        {"class_name": to_class_name(e.name), "enum_values": e.values}
        for e in document.enums
    ]
    return render("enum.py.jinja", {"enums": enums})
