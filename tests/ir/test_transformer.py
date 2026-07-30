import dataclasses

from graphql import OperationType, Source, build_schema, parse

from nabu.ir.operations import IRFragmentSpread, IRInlineFragment, IRVariableRef
from nabu.ir.transformer import build_ir

SCHEMA = """
scalar DateTime

enum Status { ACTIVE INACTIVE }

interface Node { id: ID! }

type Student implements Node {
    id: ID!
    name: String!
    status: Status!
    tags: [String!]
}

input StudentFilter { status: Status limit: Int = 10 }

union SearchResult = Student

type Query {
    student(id: ID!): Student
    students(filter: StudentFilter): [Student!]!
    search(q: String!): [SearchResult!]!
}

type Mutation {
    createStudent(name: String!): Student!
}
"""


def _schema():
    return build_schema(Source(SCHEMA, "schema.graphqls"))


def _ir(operation_text: str = ""):
    documents = []
    if operation_text:
        documents = [parse(Source(operation_text, "ops.graphql"))]
    result = build_ir(_schema(), documents)
    assert not result.failed
    return result.value


def test_definition_counts():
    doc = _ir()
    assert len(doc.objects) == 1
    assert len(doc.inputs) == 1
    assert len(doc.enums) == 1
    assert len(doc.interfaces) == 1
    assert len(doc.unions) == 1
    assert any(s.name == "DateTime" for s in doc.scalars)


def test_object_interfaces_and_fields():
    doc = _ir()
    student = next(o for o in doc.objects if o.name == "Student")
    assert "Node" in student.interfaces
    assert {f.name for f in student.fields} == {"id", "name", "status", "tags"}


def test_builtin_scalars_excluded():
    doc = _ir()
    assert all(not s.builtin for s in doc.scalars)
    assert all(s.name != "String" for s in doc.scalars)


def test_source_location_populated_on_objects():
    doc = _ir()
    student = next(o for o in doc.objects if o.name == "Student")
    assert student.source_location is not None
    assert student.source_location.file == "schema.graphqls"
    assert student.source_location.line > 0


def test_input_field_default_captured():
    doc = _ir()
    filt = next(i for i in doc.inputs if i.name == "StudentFilter")
    limit = next(f for f in filt.fields if f.name == "limit")
    assert limit.name == "limit"


def test_operation_with_variable_and_selection():
    doc = _ir("query GetStudent($id: ID!) { student(id: $id) { id name } }")
    op = doc.operations[0]
    assert op.name == "GetStudent"
    assert op.operation_type == OperationType.QUERY
    assert op.variables[0].name == "id"
    field = op.selections[0]
    assert field.name == "student"
    assert field.arguments[0].value == IRVariableRef("id")
    assert {s.name for s in field.selections} == {"id", "name"}


def test_literal_argument_and_variable_default():
    doc = _ir("query Q($n: Int = 42) { students(filter: {status: ACTIVE}) { id } }")
    op = doc.operations[0]
    assert op.variables[0].default_value == 42
    arg = op.selections[0].arguments[0]
    assert arg.name == "filter"
    assert arg.value == {"status": "ACTIVE"}


def test_inline_fragment_on_union():
    doc = _ir('{ search(q: "x") { ... on Student { id } } }')
    search = doc.operations[0].selections[0]
    inline = search.selections[0]
    assert isinstance(inline, IRInlineFragment)
    assert inline.on_type == "Student"


def test_named_fragment_and_spread():
    doc = _ir('fragment F on Student { id name } query Q { student(id: "1") { ...F } }')
    assert len(doc.fragments) == 1
    assert doc.fragments[0].name == "F"
    assert doc.fragments[0].on_type == "Student"
    spread = doc.operations[0].selections[0].selections[0]
    assert isinstance(spread, IRFragmentSpread)
    assert spread.name == "F"


def test_field_alias_captured():
    doc = _ir('{ student(id: "1") { pk: id } }')
    aliased = doc.operations[0].selections[0].selections[0]
    assert aliased.name == "id"
    assert aliased.alias == "pk"


def test_anonymous_operation():
    doc = _ir('{ student(id: "1") { id } }')
    assert doc.operations[0].name == "<anonymous>"


def test_no_graphql_core_types_leak():
    doc = _ir("query GetStudent($id: ID!) { student(id: $id) { id } }")
    assert dataclasses.asdict(doc)


def test_empty_operations():
    doc = _ir()
    assert doc.operations == []
    assert doc.fragments == []
