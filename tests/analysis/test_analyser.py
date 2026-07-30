from graphql import Source, build_schema, parse

from nabu.analysis.analyser import analyse
from nabu.config.loader import Config
from nabu.diagnostics.codes import ErrorCode
from nabu.ir.transformer import build_ir

SCHEMA = """
scalar DateTime
scalar URL

enum Status { ACTIVE INACTIVE }

interface Node { id: ID! }

type Student implements Node {
    id: ID!
    name: String!
    status: Status!
}

input CreateStudentInput {
    name: String!
}

union SearchResult = Student

type Query {
    student(id: ID!): Student
    search(q: String!): [SearchResult!]!
}

type Mutation {
    createStudent(input: CreateStudentInput!): Student!
}
"""

OPERATION = "query GetStudent($id: ID!) { student(id: $id) { id name } }"


def _ir(schema_sdl=SCHEMA, op_text=OPERATION):
    schema = build_schema(Source(schema_sdl, "schema.graphqls"))
    docs = [parse(Source(op_text, "op.graphql"))] if op_text else []
    return build_ir(schema, docs).value


def _config(**scalars):
    return Config(
        schema="schema.graphqls", operations="ops/", output="out", scalars=scalars
    )


def test_valid_schema_no_diagnostics():
    result = analyse(_ir(), _config(DateTime="datetime.datetime", URL="str"))
    assert not result.failed
    assert result.diagnostics == []


def test_unmapped_scalar_produces_e021():
    result = analyse(_ir(), _config())
    codes = [d.code for d in result.diagnostics]
    assert ErrorCode.UNMAPPED_SCALAR in codes
    assert result.failed


def test_mapped_scalar_no_diagnostic():
    result = analyse(_ir(), _config(DateTime="datetime.datetime", URL="str"))
    assert not any(d.code == ErrorCode.UNMAPPED_SCALAR for d in result.diagnostics)


def test_unknown_type_ref_check_runs():
    result = analyse(_ir(), _config(DateTime="datetime.datetime", URL="str"))
    assert not any(d.code == ErrorCode.UNKNOWN_TYPE_REF for d in result.diagnostics)


def test_unknown_field_on_root_query():
    ir = _ir(op_text="query Q { nonExistent { id } }")
    result = analyse(ir, _config(DateTime="datetime.datetime", URL="str"))
    assert any(d.code == ErrorCode.UNKNOWN_FIELD for d in result.diagnostics)


def test_unknown_nested_field():
    ir = _ir(op_text='query Q { student(id: "1") { id ghost } }')
    result = analyse(ir, _config(DateTime="datetime.datetime", URL="str"))
    assert any(d.code == ErrorCode.UNKNOWN_FIELD for d in result.diagnostics)


def test_valid_selection_no_e023():
    result = analyse(_ir(), _config(DateTime="datetime.datetime", URL="str"))
    assert not any(d.code == ErrorCode.UNKNOWN_FIELD for d in result.diagnostics)


def test_unknown_fragment_spread():
    ir = _ir(op_text='query Q { student(id: "1") { ...UndefinedFrag } }')
    result = analyse(ir, _config(DateTime="datetime.datetime", URL="str"))
    assert any(d.code == ErrorCode.UNKNOWN_FRAGMENT for d in result.diagnostics)


def test_bad_fragment_target():
    ir = _ir(
        op_text='fragment F on NonExistentType { id } query Q { student(id: "1") { ...F } }'
    )
    result = analyse(ir, _config(DateTime="datetime.datetime", URL="str"))
    assert any(d.code == ErrorCode.BAD_FRAGMENT_TARGET for d in result.diagnostics)


def test_valid_fragment_no_errors():
    ir = _ir(
        op_text='fragment F on Student { id name } query Q { student(id: "1") { ...F } }'
    )
    result = analyse(ir, _config(DateTime="datetime.datetime", URL="str"))
    assert not any(
        d.code in (ErrorCode.UNKNOWN_FRAGMENT, ErrorCode.BAD_FRAGMENT_TARGET)
        for d in result.diagnostics
    )


def test_reserved_field_name():
    schema = """
    type Query { a: T }
    type T { pass: String! }
    """
    ir = _ir(schema_sdl=schema, op_text="")
    result = analyse(ir, _config())
    assert any(d.code == ErrorCode.RESERVED_NAME for d in result.diagnostics)


def test_subscription_produces_e028():
    schema = """
    type Query { a: String }
    type Subscription { onEvent: String }
    """
    op = "subscription Sub { onEvent }"
    ir = _ir(schema_sdl=schema, op_text=op)
    result = analyse(ir, _config())
    assert any(d.code == ErrorCode.UNSUPPORTED_FEATURE for d in result.diagnostics)


def test_unmapped_scalar_has_source_location():
    result = analyse(_ir(), _config())
    scalar_diags = [
        d for d in result.diagnostics if d.code == ErrorCode.UNMAPPED_SCALAR
    ]
    assert scalar_diags
    assert scalar_diags[0].file == "schema.graphqls"
    assert scalar_diags[0].line is not None


def test_unknown_variable_type():
    ir = _ir(op_text="query Q($x: GhostType!) { student(id: $x) { id } }")
    result = analyse(ir, _config(DateTime="datetime.datetime", URL="str"))
    assert any(d.code == ErrorCode.UNKNOWN_VARIABLE_TYPE for d in result.diagnostics)


def test_name_collision():
    schema = """
    type student { id: ID! }
    type Student { id: ID! }
    type Query { a: student b: Student }
    """
    ir = _ir(schema_sdl=schema, op_text="")
    result = analyse(ir, _config())
    assert any(d.code == ErrorCode.NAME_COLLISION for d in result.diagnostics)
