import shutil
import subprocess
import sys
from importlib.resources import files

from jinja2 import BaseLoader, Environment


def _load_template(name: str) -> str:
    package = files("nabu.backends.python.codegen.templates")
    return (package / name).read_text(encoding="utf-8")


def _ruff_cmd() -> list[str]:
    """Return the ruff invocation prefix for this environment."""
    ruff = shutil.which("ruff")
    return [ruff] if ruff else [sys.executable, "-m", "ruff"]


def _ruff_format(source: str, filename: str) -> str:
    cmd = _ruff_cmd() + ["format", "--stdin-filename", filename, "-"]
    result = subprocess.run(cmd, input=source.encode("utf-8"), capture_output=True)
    return result.stdout.decode("utf-8") if result.returncode == 0 else source


def _ruff_fix(source: str, filename: str) -> str:
    """Run ruff check --select F --fix on the source to remove unused imports
    and fix other auto-fixable pyflakes issues."""
    cmd = _ruff_cmd() + [
        "check",
        "--select", "F",
        "--fix",
        "--stdin-filename", filename,
        "-",
    ]
    result = subprocess.run(cmd, input=source.encode("utf-8"), capture_output=True)
    # ruff check exits 0 (no issues) or 1 (issues found, some fixed)
    # stdout is the fixed source in both cases when using stdin
    if result.stdout:
        return result.stdout.decode("utf-8")
    return source


def render(template_name: str, context: dict) -> str:
    source = _load_template(template_name)
    env = Environment(loader=BaseLoader(), keep_trailing_newline=True)
    template = env.from_string(source)
    rendered = template.render(**context)
    filename = template_name.replace(".jinja", "")
    formatted = _ruff_format(rendered, filename)
    return _ruff_fix(formatted, filename)
