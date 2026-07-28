from pathlib import Path

from graphql import GraphQLSchema, GraphQLSyntaxError, Source, build_schema

from nabu.diagnostics.codes import ErrorCode
from nabu.diagnostics.diagnostic import Diagnostic
from nabu.diagnostics.result import Result


def parse_schema(path: Path) -> Result[GraphQLSchema]:
    # Name the Source so schema AST nodes carry the real file path in loc.source.name
    source = Source(path.read_text(encoding="utf-8"), str(path))
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
