from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.names import to_class_name
from nabu.ir.document import IRDocument


def generate_exports(document: IRDocument) -> str:
    names = (
        [
            {"module": "enums", "class_name": to_class_name(e.name)}
            for e in document.enums
        ]
        + [
            {"module": "inputs", "class_name": to_class_name(i.name)}
            for i in document.inputs
        ]
        + [
            {"module": "models", "class_name": to_class_name(o.name)}
            for o in document.objects
        ]
    )
    return render("init.py.jinja", {"names": names})
