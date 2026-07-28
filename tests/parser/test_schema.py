from pathlib import Path

from nabu.diagnostics.codes import ErrorCode
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

    result = parse_schema(f)

    assert result.value is not None
    assert not result.failed


def test_parse_schema_invalid(tmp_path: Path) -> None:
    f = tmp_path / "schema.graphqls"
    f.write_text(INVALID_SCHEMA)

    result = parse_schema(f)

    assert result.value is None
    assert result.failed

    diag = result.diagnostics[0]
    assert diag.code == ErrorCode.PARSER_SYNTAX_ERROR
    assert diag.file == str(f)
    assert diag.line is not None
