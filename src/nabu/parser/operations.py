from pathlib import Path

from graphql import DocumentNode, GraphQLSchema, GraphQLSyntaxError, parse, validate

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.reporter import Diagnostic, DiagnosticReporter


def parse_operations(
    paths: list[Path], schema: GraphQLSchema, reporter: DiagnosticReporter
) -> list[DocumentNode]:
    documents: list[DocumentNode] = []

    for path in paths:
        source = path.read_text(encoding="utf-8")

        try:
            document = parse(source)
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
            continue

        errors = validate(schema, document)
        if errors:
            for e in errors:
                reporter.add(
                    Diagnostic(
                        code=ErrorCode.PARSER_VALIDATION_ERROR,
                        severity="error",
                        message=e.message,
                        file=str(path),
                        line=e.locations[0].line if e.locations else None,
                        column=e.locations[0].column if e.locations else None,
                    )
                )
            continue

        documents.append(document)

    return documents
