from pathlib import Path

from graphql import GraphQLSchema, GraphQLSyntaxError, build_schema

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.reporter import Diagnostic, DiagnosticReporter


def parse_schema(path: Path, reporter: DiagnosticReporter) -> GraphQLSchema | None:
    source = path.read_text(encoding="utf-8")
    try:
        return build_schema(source)
    except GraphQLSyntaxError as e:
        reporter.add(
            Diagnostic(
                code=ErrorCode.PARSER_SYNTAX_ERROR,
                severity="error",
                message=e.message,
                file=str(path),
                line=e.locations[0].line if e.locations else None,
                column=e.locations[0].column if e.locations else None,
            )
        )
        return None
