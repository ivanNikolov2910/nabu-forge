from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    file: str
    line: int
    column: int


def source_location_from_node(node) -> SourceLocation | None:
    loc = getattr(node, "loc", None) if node is not None else None
    if loc is None:
        return None
    token = loc.start_token
    file = loc.source.name if loc.source else "<unknown>"
    return SourceLocation(file=file, line=token.line, column=token.column)
