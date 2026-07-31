import re

_BARE_IMPORT_MODULES = {"datetime", "decimal", "uuid", "pathlib", "enum"}


class ImportCollector:
    def __init__(self) -> None:
        self._bare: set[str] = set()
        self._from: dict[str, set[str]] = {}
        self._relative: set[str] = set()

    def add(self, annotation: str) -> str:
        tokens = re.split(r"[\s|\[\],]+", annotation)
        result = annotation
        for token in tokens:
            token = token.strip()
            if not token or token in ("None", "str", "int", "float", "bool", "list"):
                continue
            if "." in token:
                module, name = token.split(".", 1)
                module = module.strip()
                name = name.strip()
                if module in _BARE_IMPORT_MODULES:
                    self._bare.add(module)
                else:
                    self._from.setdefault(module, set()).add(name)
                    result = result.replace(token, name)
        return result

    def add_relative(self, module: str, name: str) -> None:
        """Record a relative import. module may be a plain name ('enums') or
        include leading dots for parent packages ('..enums')."""
        if module.startswith("."):
            self._relative.add(f"from {module} import {name}")
        else:
            self._relative.add(f"from .{module} import {name}")

    def render(self) -> str:
        lines: list[str] = []
        for module in sorted(self._bare):
            lines.append(f"import {module}")
        if self._bare and (self._from or self._relative):
            lines.append("")
        for module in sorted(self._from):
            names = ", ".join(sorted(self._from[module]))
            lines.append(f"from {module} import {names}")
        if self._from and self._relative:
            lines.append("")
        for stmt in sorted(self._relative):
            lines.append(stmt)
        return "\n".join(lines)
