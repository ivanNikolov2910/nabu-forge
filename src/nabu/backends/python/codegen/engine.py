import subprocess
import sys
from importlib.resources import files

from jinja2 import BaseLoader, Environment

_RUFF = [sys.executable, "-m", "ruff"]


def _load_template(name: str) -> str:
    package = files("nabu.backends.python.codegen.templates")
    return (package / name).read_text(encoding="utf-8")


def _ruff_format(source: str, filename: str) -> str:
    result = subprocess.run(
        _RUFF + ["format", "--stdin-filename", filename, "-"],
        input=source.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    return result.stdout.decode("utf-8") if result.returncode == 0 else source


def _ruff_fix(source: str, filename: str) -> str:
    result = subprocess.run(
        _RUFF + ["check", "--select", "F", "--fix", "--stdin-filename", filename, "-"],
        input=source.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    return result.stdout.decode("utf-8") if result.stdout else source


def render(template_name: str, context: dict) -> str:
    source = _load_template(template_name)
    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)
    rendered = env.from_string(source).render(**context)
    filename = template_name.replace(".jinja", "")
    formated = _ruff_format(rendered, filename)

    return _ruff_fix(formated, filename)
