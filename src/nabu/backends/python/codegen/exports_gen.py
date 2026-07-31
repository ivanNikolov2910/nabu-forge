from nabu.backends.python.codegen.engine import render
from nabu.backends.python.mapping.names import to_class_name
from nabu.ir.document import IRDocument


def generate_exports(document: IRDocument) -> str:
    # Grouped by module (enums → inputs → models), alphabetical within each group.
    # Matches the import style ruff/isort would produce.
    names = (
        sorted([{"module": "enums", "class_name": to_class_name(e.name)} for e in document.enums], key=lambda n: n["class_name"])
        + sorted([{"module": "inputs", "class_name": to_class_name(i.name)} for i in document.inputs], key=lambda n: n["class_name"])
        + sorted([{"module": "models", "class_name": to_class_name(o.name)} for o in document.objects], key=lambda n: n["class_name"])
    )
    return render("init.py.jinja", {"names": names})
