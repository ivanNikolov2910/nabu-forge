from nabu.backends.python.codegen.engine import render


def generate_exceptions() -> str:
    return render("exceptions.py.jinja", {})
