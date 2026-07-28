from pathlib import Path

from graphql import GraphQLSchema, GraphQLSyntaxError, build_schema

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result


def parse_schema(path: Path) -> Result[GraphQLSchema]:
    source = path.read_text(encoding="utf-8")
    try:
        return Result(value=build_schema(source))
    except GraphQLSyntaxError as e:
        return Result(
            diagnostics=[
                Diagnostic.from_graphql_error(e, ErrorCode.PARSER_SYNTAX_ERROR, path)
            ]
        )
    except TypeError as e:
        return Result(
            diagnostics=[
                Diagnostic(
                    code=ErrorCode.PARSER_VALIDATION_ERROR,
                    severity="error",
                    message=str(e),
                    file=str(path),
                )
            ]
        )
