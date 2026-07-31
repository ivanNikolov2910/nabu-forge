from operator import itemgetter

from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.names import to_class_name
from nabu.ir.document import IRDocument


def _entries(module: str, items) -> list[dict]:
    entries = [
        {"module": module, "class_name": to_class_name(item.name)} for item in items
    ]
    entries.sort(key=itemgetter("class_name"))
    return entries


def generate_exports(document: IRDocument) -> str:
    names = (
        _entries("enums", document.enums)
        + _entries("inputs", document.inputs)
        + _entries("models", document.objects)
    )
    return render("init.py.jinja", {"names": names})
