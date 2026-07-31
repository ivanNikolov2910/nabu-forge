from nabu.backends.python.codegen.engine import render


def generate_transport() -> str:
    return render("transport.py.jinja", {})
