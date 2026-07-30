import shutil
import subprocess
import sys
from importlib.resources import files

from jinja2 import BaseLoader, Environment


def _load_template(name: str) -> str:
    package = files("nabu.backends.python.codegen.templates")
    return (package / name).read_text(encoding="utf-8")


def _ruff_format(source: str, filename: str) -> str:
    ruff = shutil.which("ruff") or f"{sys.executable} -m ruff"
    cmd = (
        [ruff, "format", "--stdin-filename", filename, "-"]
        if shutil.which("ruff")
        else [sys.executable, "-m", "ruff", "format", "--stdin-filename", filename, "-"]
    )
    result = subprocess.run(cmd, input=source.encode("utf-8"), capture_output=True)
    return result.stdout.decode("utf-8") if result.returncode == 0 else source


def render(template_name: str, context: dict) -> str:
    source = _load_template(template_name)
    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)
    template = env.from_string(source)
    rendered = template.render(**context)
    return _ruff_format(rendered, template_name.replace(".jinja", ""))
