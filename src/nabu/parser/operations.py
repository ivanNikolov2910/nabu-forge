from pathlib import Path

from graphql import (
    DocumentNode,
    GraphQLSchema,
    GraphQLSyntaxError,
    Source,
    parse,
    validate,
)

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result


def parse_operations(
    paths: list[Path], schema: GraphQLSchema
) -> Result[list[DocumentNode]]:
    documents: list[DocumentNode] = []
    diagnostics: list[Diagnostic] = []

    for path in paths:
        source = Source(path.read_text(encoding="utf-8"), str(path))

        try:
            document = parse(source)
        except GraphQLSyntaxError as e:
            diagnostics.append(
                Diagnostic.from_graphql_error(e, ErrorCode.PARSER_SYNTAX_ERROR, path)
            )
            continue

        errors = validate(schema, document)
        if errors:
            diagnostics.extend(
                Diagnostic.from_graphql_error(
                    e, ErrorCode.PARSER_VALIDATION_ERROR, path
                )
                for e in errors
            )
            continue

        documents.append(document)

    return Result(value=documents, diagnostics=diagnostics)
