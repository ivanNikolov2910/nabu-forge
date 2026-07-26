from pathlib import Path

from nabu.diagnostics import DiagnosticReporter, ErrorCode
from nabu.parser.schema import parse_schema

VALID_SCHEMA = """
type Query {
    hello: String
}
"""

INVALID_SCHEMA = """
type Query {
    hello: String
"""


def test_parse_schema(tmp_path: Path) -> None:
    f = tmp_path / "schema.graphqls"
    f.write_text(VALID_SCHEMA)
    reporter = DiagnosticReporter()

    result = parse_schema(f, reporter)

    assert result is not None
    assert not reporter.has_errors()


def test_parse_schema_invalid(tmp_path: Path) -> None:
    f = tmp_path / "schema.graphqls"
    f.write_text(INVALID_SCHEMA)
    reporter = DiagnosticReporter()

    result = parse_schema(f, reporter)

    assert result is None
    assert reporter.has_errors()

    diag = reporter._diagnostics[0]
    assert diag.code == ErrorCode.PARSER_SYNTAX_ERROR
    assert diag.file == str(f)
    assert diag.line is not None
