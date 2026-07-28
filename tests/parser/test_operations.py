from pathlib import Path

from nabu.diagnostics.codes import ErrorCode
from nabu.parser.operations import parse_operations
from nabu.parser.schema import parse_schema

SCHEMA = """
type Query {
    student(id: ID!): Student
}

type Student {
    id: ID!
    name: String!
}
"""

VALID_OPERATION = """
query GetStudent($id: ID!) {
    student(id: $id) {
        id
        name
    }
}
"""

INVALID_SYNTAX = """
query GetStudent($id: ID!) {
    student(id: $id) {
        id
        name
"""

INVALID_FIELD = """
query GetStudent($id: ID!) {
    student(id: $id) {
        id
        nonExistentField
    }
}
"""


def _schema(tmp_path: Path):
    f = tmp_path / "schema.graphqls"
    f.write_text(SCHEMA)
    return parse_schema(f).value


def test_parse_valid_operation(tmp_path: Path) -> None:
    op = tmp_path / "op.graphql"
    op.write_text(VALID_OPERATION)

    result = parse_operations([op], _schema(tmp_path))

    assert len(result.value) == 1
    assert not result.failed


def test_syntax_error_skips_file(tmp_path: Path) -> None:
    op = tmp_path / "op.graphql"
    op.write_text(INVALID_SYNTAX)

    result = parse_operations([op], _schema(tmp_path))

    assert result.value == []
    assert result.failed
    assert result.diagnostics[0].code == ErrorCode.PARSER_SYNTAX_ERROR


def test_validation_error_skips_file(tmp_path: Path) -> None:
    op = tmp_path / "op.graphql"
    op.write_text(INVALID_FIELD)

    result = parse_operations([op], _schema(tmp_path))

    assert result.value == []
    assert result.failed
    assert result.diagnostics[0].code == ErrorCode.PARSER_VALIDATION_ERROR


def test_valid_and_invalid_files(tmp_path: Path) -> None:
    valid = tmp_path / "valid.graphql"
    invalid = tmp_path / "invalid.graphql"
    valid.write_text(VALID_OPERATION)
    invalid.write_text(INVALID_FIELD)

    result = parse_operations([valid, invalid], _schema(tmp_path))

    assert len(result.value) == 1
    assert result.failed
