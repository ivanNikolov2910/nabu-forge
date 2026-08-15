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


def test_parse_schema_type_error(tmp_path: Path) -> None:
    from unittest.mock import patch

    from nabu.diagnostics.codes import ErrorCode

    f = tmp_path / "schema.graphqls"
    f.write_text("type Query { id: ID! }")
    with patch("nabu.parser.schema.build_schema", side_effect=TypeError("bad type")):
        result = parse_schema(f)
    assert result.failed
    assert result.diagnostics[0].code == ErrorCode.PARSER_VALIDATION_ERROR
