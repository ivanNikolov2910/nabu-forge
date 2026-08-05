import importlib
import sys
from pathlib import Path

import pytest
from graphql import Source, build_schema, parse

from nabu.backends.python.codegen.enum_gen import generate_enums
from nabu.backends.python.codegen.exports_gen import generate_exports
from nabu.backends.python.codegen.input_gen import generate_inputs
from nabu.backends.python.codegen.model_gen import generate_models
from nabu.backends.python.codegen.operation_gen import (
    generate_operation,
    generate_operations,
)
from nabu.backends.python.codegen.ordering import dependency_order
from nabu.backends.python.codegen.scalars_gen import generate_scalars
from nabu.backends.python.codegen.writer import write_package
from nabu.config.loader import Config
from nabu.ir.transformer import build_ir

SCHEMA = """
scalar DateTime

enum Status { ACTIVE INACTIVE }

interface Node { id: ID! }

type Author implements Node {
    id: ID!
    name: String!
    createdAt: DateTime!
}

type Book implements Node {
    id: ID!
    title: String!
    status: Status!
    author: Author!
    tags: [String!]!
}

input CreateBookInput {
    title: String!
    authorId: ID!
}

type Query {
    book(id: ID!): Book
    author(id: ID!): Author
}

type Mutation {
    createBook(input: CreateBookInput!): Book!
}
"""

OPERATION = """
query GetBook($id: ID!) {
    book(id: $id) {
        id
        title
        status
        author {
            id
            name
        }
    }
}
"""


@pytest.fixture
def doc():
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    docs = [parse(Source(OPERATION, "op.graphql"))]
    return build_ir(schema, docs).value


@pytest.fixture
def cfg():
    return Config(
        schema="schema.graphqls",
        operations="ops/",
        output="out",
        scalars={"DateTime": "datetime.datetime"},
    )


def test_dependency_order_books_after_author(doc):
    order = dependency_order(doc)
    assert order.index("Author") < order.index("Book")


def test_dependency_order_all_types_present(doc):
    order = dependency_order(doc)
    assert "Author" in order and "Book" in order


def test_dependency_order_is_stable(doc):
    assert dependency_order(doc) == dependency_order(doc)


def test_enums_contains_class(doc):
    src = generate_enums(doc)
    assert "class Status(str, Enum)" in src


def test_enums_contains_values(doc):
    src = generate_enums(doc)
    assert 'ACTIVE = "ACTIVE"' in src
    assert 'INACTIVE = "INACTIVE"' in src


def test_enums_deterministic(doc):
    assert generate_enums(doc) == generate_enums(doc)


def test_inputs_contains_class(doc, cfg):
    src = generate_inputs(doc, cfg)
    assert "class CreateBookInput(BaseModel)" in src


def test_inputs_required_field(doc, cfg):
    src = generate_inputs(doc, cfg)
    assert "title: str" in src


def test_inputs_deterministic(doc, cfg):
    assert generate_inputs(doc, cfg) == generate_inputs(doc, cfg)


def test_models_contains_classes(doc, cfg):
    src = generate_models(doc, cfg)
    assert "class Author(BaseModel)" in src
    assert "class Book(BaseModel)" in src


def test_models_enum_relative_import(doc, cfg):
    src = generate_models(doc, cfg)
    assert "from .enums import Status" in src


def test_models_author_before_book(doc, cfg):
    src = generate_models(doc, cfg)
    assert src.index("class Author") < src.index("class Book")


def test_models_deterministic(doc, cfg):
    assert generate_models(doc, cfg) == generate_models(doc, cfg)


def test_operation_result_class(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "class GetBookResult(BaseModel)" in src


def test_operation_nested_class(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "class GetBookBookAuthor(BaseModel)" in src


def test_operation_enum_import(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    assert "from ..enums import Status" in src


def test_operation_nullable_result(doc, cfg):
    op = next(o for o in doc.operations if o.name == "GetBook")
    src = generate_operation(op, doc, cfg)
    # book field on Query is nullable (Book, not Book!)
    assert "book: GetBookBook | None" in src


def test_operations_dict_keys(doc, cfg):
    ops = generate_operations(doc, cfg)
    assert "get_book.py" in ops


def test_query_resolves_against_query_root(cfg):
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    docs = [
        parse(Source("query GetBook($id: ID!) { book(id: $id) { id } }", "op.graphql"))
    ]
    d = build_ir(schema, docs).value
    op = d.operations[0]
    src = generate_operation(op, d, cfg)
    assert "book: GetBookBook | None" in src


def test_mutation_resolves_against_mutation_root(cfg):
    schema = build_schema(Source(SCHEMA, "schema.graphqls"))
    docs = [
        parse(
            Source(
                "mutation CreateBook($input: CreateBookInput!) { createBook(input: $input) { id title } }",
                "op.graphql",
            )
        )
    ]
    d = build_ir(schema, docs).value
    op = d.operations[0]
    src = generate_operation(op, d, cfg)
    # 'createBook' exists on Mutation, not Query — must be resolved
    assert "class CreateBookCreateBook(BaseModel)" in src
    assert "create_book: CreateBookCreateBook" in src


def test_scalars_map_present(cfg):
    src = generate_scalars(cfg)
    assert "SCALAR_MAP" in src
    assert '"DateTime"' in src


def test_scalars_annotation_string_present(cfg):
    src = generate_scalars(cfg)
    assert "datetime.datetime" in src


def test_writer_creates_files(tmp_path):
    result = write_package(tmp_path, {"enums.py": "x = 1\n", "ops/a.py": "y = 2\n"})
    assert not result.failed
    assert (tmp_path / "enums.py").read_text() == "x = 1\n"
    assert (tmp_path / "ops" / "a.py").read_text() == "y = 2\n"


def test_writer_skips_identical(tmp_path):
    write_package(tmp_path, {"enums.py": "x = 1\n"})
    mtime = (tmp_path / "enums.py").stat().st_mtime
    write_package(tmp_path, {"enums.py": "x = 1\n"})
    assert (tmp_path / "enums.py").stat().st_mtime == mtime


def test_writer_overwrites_changed(tmp_path):
    write_package(tmp_path, {"enums.py": "x = 1\n"})
    write_package(tmp_path, {"enums.py": "x = 2\n"})
    assert (tmp_path / "enums.py").read_text() == "x = 2\n"


def test_generated_package_imports(doc, cfg, tmp_path):
    from nabu.backends.python.codegen.client_gen import generate_client
    from nabu.backends.python.codegen.enum_gen import generate_enums
    from nabu.backends.python.codegen.exceptions_gen import generate_exceptions
    from nabu.backends.python.codegen.input_gen import generate_inputs
    from nabu.backends.python.codegen.model_gen import generate_models
    from nabu.backends.python.codegen.operation_gen import generate_operations
    from nabu.backends.python.codegen.transport_gen import generate_transport

    files = {
        "enums.py": generate_enums(doc),
        "inputs.py": generate_inputs(doc, cfg),
        "models.py": generate_models(doc, cfg),
        "transport.py": generate_transport(),
        "exceptions.py": generate_exceptions(),
        "client.py": generate_client(doc, [], cfg),
        "__init__.py": generate_exports(doc),
    }
    for rel, content in generate_operations(doc, cfg).items():
        files[f"operations/{rel}"] = content
    write_package(tmp_path, files)

    pkg_name = "test_generated_pkg"
    spec = importlib.util.spec_from_file_location(
        pkg_name, tmp_path / "__init__.py", submodule_search_locations=[str(tmp_path)]
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = m
    spec.loader.exec_module(m)
    assert hasattr(m, "Status")
    assert hasattr(m, "Author")
    assert hasattr(m, "Client")


def test_university_end_to_end(tmp_path):
    import inspect

    from nabu.config.loader import Config
    from nabu.context import CompilerContext

    config_path = Path("samples/university/nabu.toml")
    if not config_path.exists():
        pytest.skip("university sample not found")

    ctx = CompilerContext(config_path)
    ctx.load()
    ctx.config = Config(
        schema=ctx.config.schema,
        operations=ctx.config.operations,
        output=str(tmp_path),
        scalars=ctx.config.scalars,
    )
    schema = ctx.parse_schema()
    documents = ctx.parse_operations(schema)
    ir = ctx.build_ir(schema, documents)
    ctx.analyse(ir)
    ctx.generate(ir)

    pkg_name = "university_e2e"
    spec = importlib.util.spec_from_file_location(
        pkg_name, tmp_path / "__init__.py", submodule_search_locations=[str(tmp_path)]
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name] = m
    spec.loader.exec_module(m)

    assert hasattr(m, "Client")
    client = m.Client(url="http://example.com/graphql")

    methods = [
        n
        for n, _ in inspect.getmembers(m.Client, inspect.isfunction)
        if not n.startswith("_")
    ]
    assert len(methods) == 14, f"expected 14 methods, got {methods}"

    get_student_sig = inspect.signature(client.get_student)
    params = list(get_student_sig.parameters)
    assert params == ["id"], f"get_student should take (id,), got {params}"

    list_courses_sig = inspect.signature(client.list_courses)
    list_params = list(list_courses_sig.parameters)
    assert "filter" in list_params
    assert "limit" in list_params

    assert hasattr(m, "EnrollmentStatus")
    assert hasattr(m, "CourseStatus")
