import pytest
from graphql import OperationType, build_schema

from nabu.diagnostics.reporter import DiagnosticReporter
from nabu.model.symbol_table import SymbolTable, dependency_order
from nabu.model.symbols import (
    EnumTypeSymbol,
    InputTypeSymbol,
    InterfaceTypeSymbol,
    ObjectTypeSymbol,
    ScalarTypeSymbol,
    UnionTypeSymbol,
)
from nabu.parser.operations import parse_operations

SCHEMA_SDL = """
scalar DateTime

enum EnrollmentStatus {
    ENROLLED
    ACTIVE
    GRADUATED
}

interface Node {
    id: ID!
}

type Student implements Node {
    id: ID!
    name: String!
    status: EnrollmentStatus!
    enrolledAt: DateTime!
}

type Course implements Node {
    id: ID!
    title: String!
    students: [Student!]!
}

input CreateStudentInput {
    name: String!
    status: EnrollmentStatus!
}

union SearchResult = Student | Course

type Query {
    student(id: ID!): Student
    course(id: ID!): Course
    search(q: String!): [SearchResult!]!
}

type Mutation {
    createStudent(input: CreateStudentInput!): Student!
}
"""

OPERATION = """
query GetStudent($id: ID!) {
    student(id: $id) {
        id
        name
        status
    }
}
"""


@pytest.fixture
def schema():
    return build_schema(SCHEMA_SDL)


@pytest.fixture
def table(schema, tmp_path):
    op = tmp_path / "get_student.graphql"
    op.write_text(OPERATION)
    reporter = DiagnosticReporter()
    docs = parse_operations([op], schema, reporter)
    return SymbolTable(schema, docs, DiagnosticReporter())


def test_object_type_registered(table):
    sym = table.get("Student")
    assert isinstance(sym, ObjectTypeSymbol)
    assert sym.name == "Student"


def test_object_type_fields(table):
    sym = table.get("Student")
    field_names = [f.name for f in sym.fields]
    assert "id" in field_names
    assert "name" in field_names
    assert "status" in field_names


def test_object_type_interfaces(table):
    sym = table.get("Student")
    assert "Node" in sym.interfaces


def test_enum_registered(table):
    sym = table.get("EnrollmentStatus")
    assert isinstance(sym, EnumTypeSymbol)
    assert "ENROLLED" in sym.values
    assert "GRADUATED" in sym.values


def test_scalar_registered(table):
    sym = table.get("DateTime")
    assert isinstance(sym, ScalarTypeSymbol)
    assert sym.builtin is False


def test_builtin_scalar_not_registered(table):
    assert table.get("String") is None
    assert table.get("Boolean") is None


def test_input_type_registered(table):
    sym = table.get("CreateStudentInput")
    assert isinstance(sym, InputTypeSymbol)
    field_names = [f.name for f in sym.fields]
    assert "name" in field_names


def test_interface_registered(table):
    sym = table.get("Node")
    assert isinstance(sym, InterfaceTypeSymbol)


def test_union_registered(table):
    sym = table.get("SearchResult")
    assert isinstance(sym, UnionTypeSymbol)
    assert "Student" in sym.members
    assert "Course" in sym.members


def test_resolve_type_raises_on_missing(table):
    with pytest.raises(KeyError):
        table.resolve_type("NonExistent")


def test_get_interfaces(table):
    interfaces = table.get_interfaces("Student")
    assert any(i.name == "Node" for i in interfaces)


def test_get_union_members(table):
    members = table.get_union_members("SearchResult")
    names = [m.name for m in members]
    assert "Student" in names
    assert "Course" in names


def test_operation_registered(table):
    op = table.get_operation("GetStudent")
    assert op.name == "GetStudent"
    assert op.operation_type == OperationType.QUERY


def test_operation_variables(table):
    op = table.get_operation("GetStudent")
    assert any(v.name == "id" for v in op.variables)


def test_all_operations(table):
    ops = table.all_operations()
    assert len(ops) == 1


def test_duplicate_operation(schema, tmp_path):
    op1 = tmp_path / "a.graphql"
    op2 = tmp_path / "b.graphql"
    op1.write_text(OPERATION)
    op2.write_text(OPERATION)
    reporter = DiagnosticReporter()
    docs = parse_operations([op1, op2], schema, reporter)
    dup_reporter = DiagnosticReporter()
    table = SymbolTable(schema, docs, dup_reporter)
    assert dup_reporter.has_errors()


def test_dependency_order(table):
    order = dependency_order(table)
    assert order.index("EnrollmentStatus") < order.index("Student")
    assert order.index("DateTime") < order.index("Student")
